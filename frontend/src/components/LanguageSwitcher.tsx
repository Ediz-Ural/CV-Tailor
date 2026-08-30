import { useTranslation } from 'react-i18next'

import { supportedLanguages } from '@/i18n'

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation()
  const currentLanguage = i18n.resolvedLanguage === 'en' ? 'en' : 'tr'

  return (
    <div aria-label={t('language.label')} className="flex rounded-lg border bg-background p-1">
      {supportedLanguages.map((language) => (
        <button
          aria-pressed={currentLanguage === language}
          className={`h-8 rounded-md px-3 font-mono text-xs ${currentLanguage === language ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-secondary'}`}
          key={language}
          onClick={() => void i18n.changeLanguage(language)}
          type="button"
        >
          {t(`language.${language}`)}
        </button>
      ))}
    </div>
  )
}
