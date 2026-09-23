/* ══════════════════════════════════════════════════════════════
   AQONE PROFILE SYSTEM - AUTHENTICATED OPERATOR PROFILE
   ══════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    if (typeof document !== 'undefined') {
        document.addEventListener('DOMContentLoaded', () => {
            initTabs();
            initLanguageSwitcher();
            initDarkMode();
            initHeaderAndActions();
            loadAuthenticatedUser();
        });
    }

    /* --------------------------------------------------------------
       1. TOAST NOTIFICATION ENGINE
       -------------------------------------------------------------- */
    function showToast(message, type) {
        if (typeof document === 'undefined') return;
        type = type || 'info';
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast-item toast-${type}`;

        const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';
        toast.innerHTML = `
            <span class="toast-icon">${icon}</span>
            <span class="toast-message">${escapeText(message)}</span>
        `;

        container.appendChild(toast);

        setTimeout(() => toast.classList.add('show'), 10);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    function escapeText(str) {
        if (str == null) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    /* --------------------------------------------------------------
       2. TABS SWITCHER SYSTEM
       -------------------------------------------------------------- */
    function initTabs() {
        if (typeof document === 'undefined') return;
        const tabs = document.querySelectorAll('.profile-tab');
        const tabContents = document.querySelectorAll('.profile-tab-content');

        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const targetTab = tab.getAttribute('data-tab');

                tabs.forEach(t => t.classList.remove('active'));
                tabContents.forEach(c => c.classList.remove('active'));

                tab.classList.add('active');
                const targetContent = document.getElementById(`tab-${targetTab}`);
                if (targetContent) {
                    targetContent.classList.add('active');
                }
            });
        });
    }

    /* --------------------------------------------------------------
       3. ENGLISH <-> AKLANON LANGUAGE TRANSLATOR
       -------------------------------------------------------------- */
    const translations = {
        en: {
            topTitle: "AqOne",
            topSubtitle: "My Profile",
            btnLogout: "Log Out",
            tabPersonal: "Personal Info",
            tabSecurity: "Security",
            tabPreferences: "Preferences",
            hdrPersonalInfo: "Personal Information",
            subPersonalInfo: "Authenticated operator account details.",
            lblFullName: "Full Name",
            lblRole: "System Role",
            lblEmail: "Email Address",
            lblOffice: "Office / Municipality",
            hdrSecurity: "Password & Security",
            subSecurity: "Account credentials and authentication state.",
            hdrSessions: "Active Session",
            subSessions: "Current authentication session details.",
            sessionBadge: "Current",
            hdrPref: "Preferences",
            subPref: "Browser-local display settings.",
            lblLangPref: "System Language / Eingguahe",
            descLangPref: "Choose between English and Akeanon (Aklanon). Saved in this browser.",
            lblDarkMode: "Dark Mode",
            descDarkMode: "Switch between light and dark interface themes. Saved in this browser."
        },
        akl: {
            topTitle: "AqOne",
            topSubtitle: "Akun Profile",
            btnLogout: "Mag-gwa",
            tabPersonal: "Impormasyon sa Kaugalingon",
            tabSecurity: "Sekuridad",
            tabPreferences: "Gusto / Preferensya",
            hdrPersonalInfo: "Impormasyon sa Kaugalingon",
            subPersonalInfo: "Mga detalye sa akunang account.",
            lblFullName: "Kumpletong Pangaean",
            lblRole: "Papel sa Sistema",
            lblEmail: "Email Address",
            lblOffice: "Opisina / Munisipyo",
            hdrSecurity: "Password ag Sekuridad",
            subSecurity: "Kredensyal ag estado sa pag-authenticate.",
            hdrSessions: "Aktibo nga Seksyon",
            subSessions: "Mga detalye sa kasamtangang sesyon.",
            sessionBadge: "Kasamtangan",
            hdrPref: "Gusto / Preferensya",
            subPref: "Mga setting para sa browser.",
            lblLangPref: "Eingguahe sa Sistema",
            descLangPref: "Pumili sa English o Akeanon (Aklanon). Naka-save sa daya nga browser.",
            lblDarkMode: "Madulom nga Mode (Dark Mode)",
            descDarkMode: "Mag-balhin sa maensang ag madulom nga tema. Naka-save sa daya nga browser."
        }
    };

    function setLanguage(lang) {
        if (typeof document === 'undefined') return;
        const btnEn = document.getElementById('lang-en');
        const btnAkl = document.getElementById('lang-akl');
        const selectLang = document.getElementById('pref-lang-select');

        if (lang === 'akl') {
            if (btnEn) btnEn.classList.remove('active');
            if (btnAkl) btnAkl.classList.add('active');
            if (selectLang) selectLang.value = 'akl';
        } else {
            lang = 'en';
            if (btnAkl) btnAkl.classList.remove('active');
            if (btnEn) btnEn.classList.add('active');
            if (selectLang) selectLang.value = 'en';
        }

        const dict = translations[lang] || translations.en;

        const updateText = (selector, key) => {
            const el = document.querySelector(selector);
            if (el && dict[key]) el.textContent = dict[key];
        };

        updateText('.top-subtitle', 'topSubtitle');
        updateText('#btn-logout', 'btnLogout');

        const tabs = document.querySelectorAll('.profile-tab');
        if (tabs[0]) tabs[0].textContent = dict.tabPersonal;
        if (tabs[1]) tabs[1].textContent = dict.tabSecurity;
        if (tabs[2]) tabs[2].textContent = dict.tabPreferences;

        updateText('#tab-personal .profile-panel-header h3', 'hdrPersonalInfo');
        updateText('#tab-personal .profile-panel-header p', 'subPersonalInfo');
        updateText('label[for="pf-fullname"]', 'lblFullName');
        updateText('label[for="pf-role"]', 'lblRole');
        updateText('label[for="pf-email"]', 'lblEmail');
        updateText('label[for="pf-office"]', 'lblOffice');

        updateText('#tab-security .profile-panel:nth-child(1) .profile-panel-header h3', 'hdrSecurity');
        updateText('#tab-security .profile-panel:nth-child(1) .profile-panel-header p', 'subSecurity');
        updateText('#tab-security .profile-panel:nth-child(2) .profile-panel-header h3', 'hdrSessions');
        updateText('#tab-security .profile-panel:nth-child(2) .profile-panel-header p', 'subSessions');
        updateText('.profile-session-badge', 'sessionBadge');

        updateText('#tab-preferences .profile-panel-header h3', 'hdrPref');
        updateText('#tab-preferences .profile-panel-header p', 'subPref');

        const prefRows = document.querySelectorAll('.profile-toggle-row');
        if (prefRows[0]) {
            const titleEl = prefRows[0].querySelector('.profile-toggle-title');
            const descEl = prefRows[0].querySelector('.profile-toggle-desc');
            if (titleEl) titleEl.textContent = dict.lblLangPref;
            if (descEl) descEl.textContent = dict.descLangPref;
        }
        if (prefRows[1]) {
            const titleEl = prefRows[1].querySelector('.profile-toggle-title');
            const descEl = prefRows[1].querySelector('.profile-toggle-desc');
            if (titleEl) titleEl.textContent = dict.lblDarkMode;
            if (descEl) descEl.textContent = dict.descDarkMode;
        }

        try {
            localStorage.setItem('aqone_lang', lang);
        } catch (e) {
            /* ignore storage failure */
        }
    }

    function initLanguageSwitcher() {
        if (typeof document === 'undefined') return;
        const btnEn = document.getElementById('lang-en');
        const btnAkl = document.getElementById('lang-akl');
        const selectLang = document.getElementById('pref-lang-select');

        if (btnEn) btnEn.addEventListener('click', () => setLanguage('en'));
        if (btnAkl) btnAkl.addEventListener('click', () => setLanguage('akl'));
        if (selectLang) {
            selectLang.addEventListener('change', (e) => setLanguage(e.target.value));
        }

        let savedLang = 'en';
        try {
            savedLang = localStorage.getItem('aqone_lang') || 'en';
        } catch (e) {
            /* ignore */
        }
        setLanguage(savedLang);
    }

    /* --------------------------------------------------------------
       4. DARK MODE TOGGLE
       -------------------------------------------------------------- */
    function initDarkMode() {
        if (typeof document === 'undefined') return;
        const darkToggle = document.getElementById('pref-dark-toggle');

        const applyDarkMode = (isDark) => {
            if (isDark) {
                document.body.classList.add('dark-mode');
                document.documentElement.setAttribute('data-theme', 'dark');
            } else {
                document.body.classList.remove('dark-mode');
                document.documentElement.setAttribute('data-theme', 'light');
            }
        };

        let savedDark = false;
        try {
            savedDark = localStorage.getItem('aqone_dark_mode') === 'true';
        } catch (e) {
            /* ignore */
        }

        if (darkToggle) {
            darkToggle.checked = savedDark;
            darkToggle.addEventListener('change', (e) => {
                const isDark = e.target.checked;
                applyDarkMode(isDark);
                try {
                    localStorage.setItem('aqone_dark_mode', isDark);
                } catch (err) {
                    /* ignore */
                }
                showToast(isDark ? 'Dark mode enabled' : 'Light mode enabled', 'info');
            });
        }
        applyDarkMode(savedDark);
    }

    /* --------------------------------------------------------------
       5. HEADER ACTIONS & LOGOUT
       -------------------------------------------------------------- */
    function initHeaderAndActions() {
        if (typeof document === 'undefined') return;
        const notifBtn = document.getElementById('btn-notifications');
        const logoutBtn = document.getElementById('btn-logout');

        if (notifBtn) {
            notifBtn.addEventListener('click', () => {
                showToast('You have no new notifications', 'info');
            });
        }

        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                if (confirm('Are you sure you want to log out?')) {
                    showToast('Logging out...', 'info');
                    try {
                        const token = sessionStorage.getItem('aqoneToken');
                        if (token) {
                            fetch('/api/logout', {
                                method: 'POST',
                                headers: { 'Authorization': 'Bearer ' + token }
                            }).catch(() => {});
                        }
                    } catch (e) {
                        /* ignore */
                    }
                    try {
                        sessionStorage.removeItem('aqoneToken');
                        sessionStorage.removeItem('aqoneUser');
                        sessionStorage.removeItem('aqoneDemoBypassActive');
                    } catch (e) {
                        /* ignore */
                    }
                    setTimeout(() => {
                        window.location.href = 'login.html';
                    }, 500);
                }
            });
        }
    }

    /* --------------------------------------------------------------
       6. AUTHENTICATED USER IDENTITY (LOAD & RENDER)
       -------------------------------------------------------------- */
    function getInitials(name) {
        if (!name) return 'OP';
        const parts = name.trim().split(/[\s@._-]+/).filter(Boolean);
        if (parts.length >= 2) {
            return (parts[0][0] + parts[1][0]).toUpperCase();
        }
        return name.slice(0, 2).toUpperCase();
    }

    function formatRoleName(role) {
        if (!role) return 'Operator';
        const lower = String(role).toLowerCase();
        if (lower === 'admin') return 'Administrator';
        if (lower === 'mdrrmo') return 'MDRRMO Officer';
        if (lower === 'coastguard') return 'Coast Guard Watchstander';
        if (lower === 'bfar') return 'BFAR Officer';
        return role.charAt(0).toUpperCase() + role.slice(1);
    }

    function renderUserProfile(user) {
        if (typeof document === 'undefined' || !user) return;
        const displayName = user.name || user.full_name || user.email || 'Operator';
        const roleName = formatRoleName(user.role);
        const initials = getInitials(displayName);

        // Header user dropdown
        const headerName = document.getElementById('header-user-name');
        const headerRole = document.getElementById('header-user-role');
        const headerAvatar = document.getElementById('header-user-avatar');
        if (headerName) headerName.textContent = displayName;
        if (headerRole) headerRole.textContent = roleName;
        if (headerAvatar) headerAvatar.textContent = initials;

        // Profile sidebar card
        const cardName = document.getElementById('profile-card-name');
        const cardRole = document.getElementById('profile-card-role');
        const cardAvatar = document.getElementById('profile-card-avatar');
        const statRole = document.getElementById('stat-role');
        const statAuth = document.getElementById('stat-auth');

        if (cardName) cardName.textContent = displayName;
        if (cardRole) cardRole.textContent = roleName;
        if (cardAvatar) cardAvatar.textContent = initials;
        if (statRole) statRole.textContent = roleName;
        if (statAuth) statAuth.textContent = 'Active';

        // Personal info form (read-only)
        const pfName = document.getElementById('pf-fullname');
        const pfRole = document.getElementById('pf-role');
        const pfEmail = document.getElementById('pf-email');
        const pfOffice = document.getElementById('pf-office');

        if (pfName) pfName.value = displayName;
        if (pfRole) pfRole.value = roleName;
        if (pfEmail) pfEmail.value = user.email || '--';
        if (pfOffice) pfOffice.value = 'New Washington, Aklan';

        // Active session details
        const sessionMeta = document.getElementById('profile-session-meta');
        if (sessionMeta) {
            sessionMeta.textContent = 'Authenticated via Bearer Token · Active now';
        }
    }

    function loadAuthenticatedUser() {
        if (typeof window === 'undefined' || typeof sessionStorage === 'undefined') return;

        let token = null;
        let cachedUser = null;

        try {
            token = sessionStorage.getItem('aqoneToken');
            const storedUser = sessionStorage.getItem('aqoneUser');
            if (storedUser) cachedUser = JSON.parse(storedUser);
        } catch (e) {
            console.warn('[AqOne] Storage read error in profile:', e.message);
        }

        if (!token) {
            window.location.replace('login.html');
            return;
        }

        // Render cached session immediately to avoid placeholder flash
        if (cachedUser) {
            renderUserProfile(cachedUser);
        }

        // If not a local demo bypass, refresh identity from /api/me
        const isDemo = sessionStorage.getItem('aqoneDemoBypassActive') === '1' || token === 'DEMO-OFFLINE-NO-AUTH';
        if (isDemo) {
            if (!cachedUser) {
                renderUserProfile({ name: 'Demo Operator', role: 'admin', email: 'demo@aqone.local' });
            }
            return;
        }

        fetch('/api/me', {
            headers: {
                'Authorization': 'Bearer ' + token,
                'Accept': 'application/json'
            }
        })
        .then(function (res) {
            if (res.status === 401) {
                try {
                    sessionStorage.removeItem('aqoneToken');
                    sessionStorage.removeItem('aqoneUser');
                } catch (e) {
                    /* ignore */
                }
                window.location.replace('login.html');
                return null;
            }
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json();
        })
        .then(function (data) {
            if (data && data.user) {
                const updated = Object.assign({}, cachedUser || {}, data.user);
                try {
                    sessionStorage.setItem('aqoneUser', JSON.stringify(updated));
                } catch (e) {
                    /* ignore */
                }
                renderUserProfile(updated);
            }
        })
        .catch(function (err) {
            console.warn('[AqOne] Could not refresh /api/me:', err.message);
        });
    }

    // Export for unit tests under Node
    const api = {
        getInitials: getInitials,
        formatRoleName: formatRoleName,
        renderUserProfile: renderUserProfile,
        loadAuthenticatedUser: loadAuthenticatedUser,
        setLanguage: setLanguage,
        translations: translations,
        showToast: showToast
    };

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    }
    if (typeof window !== 'undefined') {
        window.AqOneProfile = api;
    }
})();
