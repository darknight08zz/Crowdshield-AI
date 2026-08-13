import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import * as SecureStore from 'expo-secure-store';
import en from '../locales/en.json';
import hi from '../locales/hi.json';

const LANGUAGE_KEY = 'user_language';

export async function getStoredLanguage(): Promise<string> {
  try {
    const stored = await SecureStore.getItemAsync(LANGUAGE_KEY);
    if (stored && (stored === 'en' || stored === 'hi')) {
      return stored;
    }
  } catch (e) {
    console.warn('[i18n] Error reading stored language from SecureStore:', e);
  }
  return 'en';
}

export async function setAppLanguage(lang: 'en' | 'hi') {
  try {
    await SecureStore.setItemAsync(LANGUAGE_KEY, lang);
    await i18n.changeLanguage(lang);
    console.log('[i18n] Active language updated and persisted to SecureStore:', lang);
  } catch (e) {
    console.warn('[i18n] Error setting app language:', e);
  }
}

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    hi: { translation: hi },
  },
  lng: 'en',
  fallbackLng: 'en',
  interpolation: {
    escapeValue: false,
  },
  react: {
    useSuspense: false,
  },
});

// Load stored language preference on app init
getStoredLanguage().then((lang) => {
  if (lang && lang !== i18n.language) {
    i18n.changeLanguage(lang);
  }
});

export default i18n;
