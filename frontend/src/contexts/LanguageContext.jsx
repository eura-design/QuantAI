import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { translations } from '../translations';

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
    const detectLanguage = () => {
        const browserLang = navigator.language || navigator.userLanguage;
        return browserLang.toLowerCase().startsWith('ko') ? 'ko' : 'en';
    };

    const [lang, setLang] = useState(detectLanguage());

    const t = useCallback((path) => {
        const keys = path.split('.');
        let result = translations[lang];
        for (const key of keys) {
            if (result[key]) {
                result = result[key];
            } else {
                return path; // 키를 찾지 못하면 경로 반환
            }
        }
        return result;
    }, [lang]);

    return (
        <LanguageContext.Provider value={{ lang, setLang, t }}>
            {children}
        </LanguageContext.Provider>
    );
}

export function useLanguage() {
    const context = useContext(LanguageContext);
    if (!context) {
        throw new Error('useLanguage must be used within a LanguageProvider');
    }
    return context;
}
