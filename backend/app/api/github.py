from collections.abc import Callable
from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.config import settings
from app.core.security import create_github_oauth_state, decode_github_oauth_state, encrypt_github_token
from app.db.session import get_db
from app.models.github_connection import GitHubConnection
from app.schemas.github import GitHubOAuthCallbackResponse, GitHubOAuthStartResponse, GitHubSyncResponse
from app.graphs.pool_graph import run_pool_graph_for_user
from app.services.github import GitHubAPIClient, GitHubAPIError, GitHubConfigurationError

router = APIRouter(prefix="/github", tags=["github"])
DbSession = Annotated[Session, Depends(get_db)]
GitHubSyncScheduler = Callable[[BackgroundTasks, UUID], None]


def get_github_oauth_client() -> GitHubAPIClient:
    return GitHubAPIClient()


def schedule_github_sync(background_tasks: BackgroundTasks, user_id: UUID) -> None:
    background_tasks.add_task(run_pool_graph_for_user, user_id, None, True)


def get_github_sync_scheduler() -> GitHubSyncScheduler:
    return schedule_github_sync


GitHubOAuthClientDependency = Annotated[GitHubAPIClient, Depends(get_github_oauth_client)]
GitHubSyncSchedulerDependency = Annotated[GitHubSyncScheduler, Depends(get_github_sync_scheduler)]


@router.post("/oauth/start", response_model=GitHubOAuthStartResponse)
def start_github_oauth(current_user: CurrentUser) -> GitHubOAuthStartResponse:
    if not settings.github_oauth_client_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="GitHub OAuth yapilandirilmamis")
    state = create_github_oauth_state(current_user.id)
    query = urlencode(
        {
            "client_id": settings.github_oauth_client_id,
            "redirect_uri": settings.github_oauth_redirect_uri,
            "scope": "repo:status read:user",
            "state": state,
        }
    )
    return GitHubOAuthStartResponse(
        authorization_url=f"https://github.com/login/oauth/authorize?{query}",
        state=state,
    )


@router.get("/oauth/callback", response_model=GitHubOAuthCallbackResponse, status_code=status.HTTP_202_ACCEPTED)
async def github_oauth_callback(
    background_tasks: BackgroundTasks,
    db: DbSession,
    github_client: GitHubOAuthClientDependency,
    sync_scheduler: GitHubSyncSchedulerDependency,
    code: str = Query(min_length=1),
    state: str = Query(min_length=1),
) -> GitHubOAuthCallbackResponse:
    try:
        user_id = decode_github_oauth_state(state)
    except (JWTError, KeyError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gecersiz GitHub OAuth state") from None

    try:
        token = await github_client.exchange_code_for_token(code)
        github_client.token = token
        username = await github_client.get_authenticated_username()
        encrypted_token = encrypt_github_token(token)
    except (GitHubConfigurationError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except GitHubAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="GitHub OAuth cagrisi basarisiz") from exc

    connection = db.scalar(select(GitHubConnection).where(GitHubConnection.user_id == user_id))
    if connection is None:
        connection = GitHubConnection(user_id=user_id, github_username=username, access_token_encrypted=encrypted_token)
        db.add(connection)
    else:
        connection.github_username = username
        connection.access_token_encrypted = encrypted_token
    db.commit()

    sync_scheduler(background_tasks, user_id)
    return GitHubOAuthCallbackResponse(github_username=username, sync_queued=True)


@router.post("/sync", response_model=GitHubSyncResponse, status_code=status.HTTP_202_ACCEPTED)
def queue_github_sync(
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    sync_scheduler: GitHubSyncSchedulerDependency,
) -> GitHubSyncResponse:
    sync_scheduler(background_tasks, current_user.id)
    return GitHubSyncResponse(queued=True)
