from collections.abc import Callable
from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.config import settings
from app.core.security import create_github_oauth_state, decode_github_oauth_state, encrypt_github_token
from app.db.session import get_db
from app.models.github_connection import GitHubConnection
from app.schemas.github import GitHubOAuthStartResponse, GitHubSyncResponse
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


def _callback_redirect(**params: str) -> RedirectResponse:
    """Send the browser back into the app instead of leaving it on a JSON body.

    GitHub redirects the user agent here, so the response has to be a page the
    user can continue from. The result is passed to the pool screen as query
    parameters.
    """
    base = settings.frontend_base_url.rstrip("/")
    return RedirectResponse(
        url=f"{base}/pool?{urlencode(params)}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/oauth/callback")
async def github_oauth_callback(
    background_tasks: BackgroundTasks,
    db: DbSession,
    github_client: GitHubOAuthClientDependency,
    sync_scheduler: GitHubSyncSchedulerDependency,
    code: str = Query(min_length=1),
    state: str = Query(min_length=1),
) -> RedirectResponse:
    try:
        user_id = decode_github_oauth_state(state)
    except (JWTError, KeyError, TypeError, ValueError):
        return _callback_redirect(github="error", reason="invalid_state")

    try:
        token = await github_client.exchange_code_for_token(code)
        github_client.token = token
        username = await github_client.get_authenticated_username()
        encrypted_token = encrypt_github_token(token)
    except (GitHubConfigurationError, ValueError):
        return _callback_redirect(github="error", reason="not_configured")
    except GitHubAPIError:
        return _callback_redirect(github="error", reason="github_unavailable")

    connection = db.scalar(select(GitHubConnection).where(GitHubConnection.user_id == user_id))
    if connection is None:
        connection = GitHubConnection(user_id=user_id, github_username=username, access_token_encrypted=encrypted_token)
        db.add(connection)
    else:
        connection.github_username = username
        connection.access_token_encrypted = encrypted_token
    db.commit()

    sync_scheduler(background_tasks, user_id)
    return _callback_redirect(github="connected", username=username)


@router.post("/sync", response_model=GitHubSyncResponse, status_code=status.HTTP_202_ACCEPTED)
def queue_github_sync(
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    sync_scheduler: GitHubSyncSchedulerDependency,
) -> GitHubSyncResponse:
    sync_scheduler(background_tasks, current_user.id)
    return GitHubSyncResponse(queued=True)
