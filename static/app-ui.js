/**
 * Smart Community - Advanced Interactive UI & Animation Engine
 */

// 1. Ambient Cursor Glow Spotlight
function initAmbientCursorGlow() {
    if (window.matchMedia('(pointer: coarse)').matches) return; // Skip on pure touch screens
    let glow = document.getElementById('ambientCursorGlow');
    if (!glow) {
        glow = document.createElement('div');
        glow.id = 'ambientCursorGlow';
        glow.className = 'ambient-cursor-glow';
        document.body.appendChild(glow);
    }

    let targetX = -500, targetY = -500;
    let currentX = -500, currentY = -500;
    let isVisible = false;
    let isHoveringInteractive = false;

    window.addEventListener('mousemove', (e) => {
        targetX = e.clientX;
        targetY = e.clientY;
        if (!isVisible) {
            isVisible = true;
            glow.style.opacity = '1';
        }
    }, { passive: true });

    document.addEventListener('mouseleave', () => {
        glow.style.opacity = '0';
        isVisible = false;
    });

    document.addEventListener('mouseover', (e) => {
        if (e.target.closest('button, a, input, select, textarea, .card, .kpi-card, .stat-card, .btn-luxury-primary, .btn-luxury-gold')) {
            isHoveringInteractive = true;
            glow.style.transform = `translate3d(${currentX}px, ${currentY}px, 0) scale(1.25)`;
        } else {
            isHoveringInteractive = false;
            glow.style.transform = `translate3d(${currentX}px, ${currentY}px, 0) scale(1)`;
        }
    }, { passive: true });

    function renderGlowLoop() {
        if (isVisible) {
            currentX += (targetX - currentX) * 0.14;
            currentY += (targetY - currentY) * 0.14;
            const scale = isHoveringInteractive ? 1.25 : 1;
            glow.style.transform = `translate3d(${currentX.toFixed(1)}px, ${currentY.toFixed(1)}px, 0) scale(${scale})`;
        }
        requestAnimationFrame(renderGlowLoop);
    }
    requestAnimationFrame(renderGlowLoop);
}

// 2. Button Sparkle Micro-Particles
function spawnButtonSparkles(x, y) {
    const colors = ['#C5A059', '#F59E0B', '#38BDF8', '#E879F9', '#10B981'];
    const sparkCount = 8;
    for (let i = 0; i < sparkCount; i++) {
        const spark = document.createElement('div');
        spark.className = 'button-sparkle';
        const size = Math.random() * 4 + 3;
        spark.style.width = `${size}px`;
        spark.style.height = `${size}px`;
        spark.style.left = `${x}px`;
        spark.style.top = `${y}px`;
        const color = colors[Math.floor(Math.random() * colors.length)];
        spark.style.background = color;
        spark.style.boxShadow = `0 0 10px ${color}`;

        const angle = (Math.PI * 2 * i) / sparkCount + (Math.random() - 0.5) * 0.6;
        const distance = Math.random() * 40 + 20;
        const tx = Math.cos(angle) * distance;
        const ty = Math.sin(angle) * distance;

        spark.style.setProperty('--spark-tx', `${tx.toFixed(1)}px`);
        spark.style.setProperty('--spark-ty', `${ty.toFixed(1)}px`);

        document.body.appendChild(spark);
        setTimeout(() => spark.remove(), 700);
    }
}

// 3. Card 3D Magnetic Tilt & Specular Glare Effect
function initCardTiltEffects(container = document) {
    const cards = container.querySelectorAll('.card-tilt, .card, .dashboard-card, .stat-card, .kpi-card, .match-item, .person-item, .post-card, .service-card, .feature-card, .auth-box-modern, .page-card');
    cards.forEach(card => {
        if (card._tiltAttached) return;
        card._tiltAttached = true;

        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            const rotateX = ((y - centerY) / centerY) * -5;
            const rotateY = ((x - centerX) / centerX) * 5;

            card.style.setProperty('--card-glare-x', `${x}px`);
            card.style.setProperty('--card-glare-y', `${y}px`);
            card.style.transform = `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateY(-5px) scale3d(1.015, 1.015, 1.015)`;
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0) scale3d(1, 1, 1)';
            card.style.setProperty('--card-glare-x', `-500px`);
            card.style.setProperty('--card-glare-y', `-500px`);
        });
    });
}

// 4. Animated Number Counters
function initAnimatedCounters(container = document) {
    const counters = container.querySelectorAll('.animate-counter');
    if (counters.length === 0) return;

    const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                if (!el._hasAnimated) {
                    el._hasAnimated = true;
                    const targetNum = parseFloat(el.getAttribute('data-target') || el.innerText.replace(/[^0-9.]/g, ''));
                    if (!isNaN(targetNum)) {
                        animateCount(el, targetNum);
                    }
                }
                obs.unobserve(el);
            }
        });
    }, { threshold: 0.15 });

    counters.forEach(c => observer.observe(c));
}

function animateCount(el, target) {
    let start = 0;
    const duration = 1200;
    const startTime = performance.now();
    const isDecimal = target % 1 !== 0;

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const currentVal = start + (target - start) * easeOut;

        el.innerText = isDecimal ? currentVal.toFixed(1) : Math.floor(currentVal);

        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            el.innerText = isDecimal ? target.toFixed(1) : target;
        }
    }
    requestAnimationFrame(update);
}

// 5. Global Animation Refresher for Dynamic Ajax / SPA Views
window.refreshUIAnimations = function(container = document) {
    initCardTiltEffects(container);
    initAnimatedCounters(container);
    
    // Auto-stagger cascade items
    const cascadeItems = container.querySelectorAll('.cascade-item');
    cascadeItems.forEach((item, index) => {
        if (!item.style.animationDelay) {
            item.style.animationDelay = `${(index * 0.05).toFixed(2)}s`;
        }
    });

    const currentTheme = localStorage.getItem('smart-community-theme') || 'light';
    updateThemeButtonUI(currentTheme);
};

document.addEventListener('DOMContentLoaded', () => {
    // Ambient Cursor Glow Spotlight
    initAmbientCursorGlow();

    // Interactive Ripple Effect & Sparkles for Buttons
    document.addEventListener('click', function (e) {
        const target = e.target.closest('.btn-luxury-primary, .btn-luxury-gold, .btn-luxury-outline, .btn-luxury-emerald, .btn-luxury-rose, .btn, button, .ripple-btn');
        if (!target) return;

        // Spawn Sparkle Micro-particles
        spawnButtonSparkles(e.clientX, e.clientY);

        const rect = target.getBoundingClientRect();
        const ripple = document.createElement('span');
        ripple.classList.add('ripple');

        const diameter = Math.max(rect.width, rect.height);
        const radius = diameter / 2;

        ripple.style.width = ripple.style.height = `${diameter}px`;
        ripple.style.left = `${e.clientX - rect.left - radius}px`;
        ripple.style.top = `${e.clientY - rect.top - radius}px`;

        target.appendChild(ripple);

        setTimeout(() => {
            ripple.remove();
        }, 600);
    });

    // Initial card tilt, counters, and cascade animations
    window.refreshUIAnimations();

    // 4. Global Modern Toast Manager
    window.showModernToast = function(message, type = 'gold') {
        let container = document.getElementById('modernToastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'modernToastContainer';
            container.className = 'toast-container-modern';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = 'toast-modern';
        
        let icon = '✨';
        if (type === 'success' || type === 'emerald') icon = '✓';
        if (type === 'danger' || type === 'rose') icon = '✕';
        if (type === 'info' || type === 'cyan') icon = 'ℹ';
        
        toast.innerHTML = `
            <span style="font-size: 16px; font-weight: bold; color: #C5A059;">${icon}</span>
            <div style="flex: 1;">${message}</div>
            <button style="background: none; border: none; color: #A0AEC0; cursor: pointer; font-size: 14px; margin-left: 8px;" onclick="this.parentElement.remove()">✕</button>
        `;

        if (type === 'danger' || type === 'rose') {
            toast.style.borderLeftColor = '#EF4444';
        } else if (type === 'success' || type === 'emerald') {
            toast.style.borderLeftColor = '#10B981';
        }

        container.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('hide');
            setTimeout(() => toast.remove(), 400);
        }, 4000);
    };

    // 5. Password Visibility Toggle
    document.querySelectorAll('.toggle-password-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const input = this.previousElementSibling || document.querySelector(this.getAttribute('data-target'));
            if (input && input.tagName === 'INPUT') {
                if (input.type === 'password') {
                    input.type = 'text';
                    this.innerHTML = '👁️';
                } else {
                    input.type = 'password';
                    this.innerHTML = '👁️‍🗨️';
                }
            }
        });
    });

    // 6. Interactive Live Filter / Search for Cards & Tables
    const searchInputs = document.querySelectorAll('[data-live-filter]');
    searchInputs.forEach(input => {
        const targetSelector = input.getAttribute('data-live-filter');
        input.addEventListener('input', () => {
            const query = input.value.toLowerCase().trim();
            const items = document.querySelectorAll(targetSelector);
            items.forEach(item => {
                const text = item.innerText.toLowerCase();
                if (text.includes(query)) {
                    item.style.display = '';
                    item.classList.add('animate-fade-in');
                } else {
                    item.style.display = 'none';
                }
            });
        });
    });

    // 7. DYNAMIC WAVE GLOW ANIMATION BACKGROUND (Every page of the application)
    initCommunityBackgroundAnimation();

    // 8. TOP-RIGHT UTILITY CONTROLS: MARATHI / ENGLISH TRANSLATOR & DARK MODE
    initThemeManager();
    initLanguageManager();
    initTopRightUtilityBar();
});

function initCommunityBackgroundAnimation() {
    // Universal background: Active across all pages of the application
    let bg = document.getElementById('communityAnimationBg');
    if (!bg) {
        bg = document.createElement('div');
        bg.id = 'communityAnimationBg';
        bg.className = 'wave-animation-bg';
        bg.innerHTML = `
            <div class="wave-base-layer" id="waveBaseLayer"></div>
            <div class="wave-flow-sheen"></div>
            <div class="wave-glow-aura" id="waveGlowAura"></div>
            <canvas id="skyParticleCanvas" class="sky-particle-canvas"></canvas>
            <div class="wave-readability-veil"></div>
        `;
        document.body.prepend(bg);
    }

    // Dynamic Bokeh Orbs, Stardust & Mouse Parallax System
    const waveBase = document.getElementById('waveBaseLayer');
    const waveAura = document.getElementById('waveGlowAura');
    const canvas = document.getElementById('skyParticleCanvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    let mouseX = width / 2;
    let mouseY = height / 2;
    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;

    window.addEventListener('mousemove', (e) => {
        const cx = width / 2;
        const cy = height / 2;
        targetX = ((e.clientX - cx) / cx) * 20; // max +/- 20px shift
        targetY = ((e.clientY - cy) / cy) * 16;
    }, { passive: true });

    window.addEventListener('resize', () => {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
    });

    // Particle creation: Golden bokeh orbs + Cyan/Magenta stardust
    const particleCount = Math.min(Math.floor((width * height) / 28000), 48);
    const particles = [];

    for (let i = 0; i < particleCount; i++) {
        const isBokeh = Math.random() < 0.28; // 28% are large glowing golden bokeh orbs
        const isCyan = Math.random() < 0.65;
        
        particles.push({
            isBokeh: isBokeh,
            x: Math.random() * width,
            y: Math.random() * height,
            radius: isBokeh ? (10 + Math.random() * 22) : (1.4 + Math.random() * 2.8),
            baseRadius: isBokeh ? (10 + Math.random() * 22) : (1.4 + Math.random() * 2.8),
            alpha: isBokeh ? (0.18 + Math.random() * 0.35) : (0.35 + Math.random() * 0.55),
            speedY: isBokeh ? -(0.15 + Math.random() * 0.35) : -(0.3 + Math.random() * 0.7),
            speedX: (Math.random() - 0.5) * (isBokeh ? 0.25 : 0.6),
            pulse: Math.random() * Math.PI * 2,
            pulseSpeed: 0.015 + Math.random() * 0.03,
            colorType: isBokeh ? 'gold' : (isCyan ? 'cyan' : 'magenta')
        });
    }

    function renderWaveScene() {
        // Smooth physics-damped parallax interpolation
        currentX += (targetX - currentX) * 0.05;
        currentY += (targetY - currentY) * 0.05;

        if (waveBase) {
            waveBase.style.transform = `translate3d(${currentX.toFixed(2)}px, ${currentY.toFixed(2)}px, 0)`;
        }
        if (waveAura) {
            waveAura.style.transform = `translate(calc(-50% + ${(currentX * 1.5).toFixed(2)}px), calc(-50% + ${(currentY * 1.5).toFixed(2)}px))`;
        }

        ctx.clearRect(0, 0, width, height);

        for (let i = 0; i < particles.length; i++) {
            const p = particles[i];
            p.y += p.speedY;
            p.x += p.speedX;
            p.pulse += p.pulseSpeed;

            // Soft sine oscillation mimicking the flowing wave
            p.x += Math.sin(p.pulse) * 0.2;

            if (p.y < -40) {
                p.y = height + 30;
                p.x = Math.random() * width;
            }
            if (p.x < -30) p.x = width + 20;
            if (p.x > width + 30) p.x = -20;

            const currentAlpha = Math.max(0.04, p.alpha + Math.sin(p.pulse) * 0.15);
            const currentRadius = Math.max(0.8, p.baseRadius + Math.sin(p.pulse * 0.8) * (p.isBokeh ? 3 : 0.6));

            ctx.save();
            ctx.beginPath();
            ctx.arc(p.x, p.y, currentRadius, 0, Math.PI * 2);

            if (p.isBokeh) {
                // Radiant golden bokeh disc with soft feathered edge
                const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, currentRadius);
                grad.addColorStop(0, `rgba(255, 235, 175, ${currentAlpha})`);
                grad.addColorStop(0.5, `rgba(245, 180, 80, ${currentAlpha * 0.7})`);
                grad.addColorStop(1, `rgba(240, 160, 50, 0)`);
                ctx.fillStyle = grad;
                ctx.shadowColor = 'rgba(251, 191, 36, 0.45)';
                ctx.shadowBlur = 12;
            } else if (p.colorType === 'cyan') {
                // Electric cyan spark stardust
                ctx.fillStyle = `rgba(56, 189, 248, ${currentAlpha})`;
                ctx.shadowColor = 'rgba(56, 189, 248, 0.8)';
                ctx.shadowBlur = 7;
            } else {
                // Magenta-pink ethereal twinkle
                ctx.fillStyle = `rgba(232, 121, 249, ${currentAlpha})`;
                ctx.shadowColor = 'rgba(232, 121, 249, 0.8)';
                ctx.shadowBlur = 7;
            }

            ctx.fill();
            ctx.restore();
        }

        requestAnimationFrame(renderWaveScene);
    }

    requestAnimationFrame(renderWaveScene);
}

/* ==========================================================================
   8. THEME & DARK MODE MANAGER
   ========================================================================== */
function initThemeManager() {
    const savedTheme = localStorage.getItem('smart-community-theme') || 'light';
    applyTheme(savedTheme, false);
}

function applyTheme(theme, updateStorage = true) {
    if (theme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        document.body.setAttribute('data-theme', 'dark');
    } else {
        document.documentElement.removeAttribute('data-theme');
        document.body.removeAttribute('data-theme');
    }
    if (updateStorage) {
        localStorage.setItem('smart-community-theme', theme);
    }
    updateThemeButtonUI(theme);
}

window.toggleAppTheme = function() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const newTheme = isDark ? 'light' : 'dark';
    applyTheme(newTheme, true);
    if (window.showModernToast) {
        const currentLang = localStorage.getItem('smart-community-lang') || 'en';
        const msg = currentLang === 'mr' 
            ? (newTheme === 'dark' ? 'डार्क मोड सक्रिय झाला 🌙' : 'लाईट मोड सक्रिय झाला ☀️')
            : (newTheme === 'dark' ? 'Dark Mode Activated 🌙' : 'Light Mode Activated ☀️');
        showModernToast(msg, 'gold');
    }
};

function updateThemeButtonUI(theme) {
    const btns = document.querySelectorAll('.theme-toggle-btn');
    btns.forEach(btn => {
        const icon = btn.querySelector('.theme-icon');
        const text = btn.querySelector('.theme-text');
        const currentLang = localStorage.getItem('smart-community-lang') || 'en';
        if (theme === 'dark') {
            if (icon) icon.textContent = '☀️';
            if (text) text.textContent = currentLang === 'mr' ? 'लाईट' : 'Light';
            btn.setAttribute('title', 'Switch to Light Mode');
        } else {
            if (icon) icon.textContent = '🌙';
            if (text) text.textContent = currentLang === 'mr' ? 'डार्क' : 'Dark';
            btn.setAttribute('title', 'Switch to Dark Mode');
        }
    });
}

/* ==========================================================================
   9. MARATHI & ENGLISH TRANSLATOR ENGINE
   ========================================================================== */
const MARATHI_DICTIONARY = {
    // Navigation items
    "Overview": "अवलोकन",
    "Create Post": "पोस्ट तयार करा",
    "Publish Notice": "नोटीस प्रकाशित करा",
    "My Posts": "माझ्या पोस्ट्स",
    "Find Matches": "मॅचेस शोधा",
    "Messages": "संदेश",
    "Residents": "रहिवासी",
    "Feedback": "अभिप्राय",
    "Notifications": "सूचना",
    "My Profile": "माझे प्रोफाइल",
    "Edit Profile": "प्रोफाइल संपादित करा",
    "Sign Out": "लॉग आउट",
    "Logout": "लॉग आउट",
    "Login": "लॉग इन",
    "Register": "नोंदणी करा",
    "Services": "सेवा",
    "Suggestions": "सूचना",
    "Admin Panel": "प्रशासक पॅनेल",
    
    // Header & Greeting
    "Good morning": "शुभ प्रभात",
    "Good afternoon": "शुभ दुपार",
    "Good evening": "शुभ संध्याकाळ",
    "Community Portal": "कम्युनिटी पोर्टल",
    "Trust Score": "विश्वास गुण",
    "Trust Metrics": "विश्वास मेट्रिक्स",
    "Verified Peer Rating": "सत्यापित रेटिंग",
    "Unread Messages": "न वाचलेले संदेश",
    "Direct Communications": "थेट संवाद",
    "Match Opportunities": "मॅच संधी",
    "AI Precision Matches": "एआय प्रिसिजन मॅचेस",
    
    // Buttons & Actions
    "Discover Residents": "रहिवासी शोधा",
    "View Smart Matches": "स्मार्ट मॅचेस पहा",
    "Message Now": "आता संदेश पाठवा",
    "Direct Message": "थेट संदेश",
    "Connect": "संपर्क साधा",
    "View Profile": "प्रोफाइल पहा",
    "Send Message": "संदेश पाठवा",
    "Search": "शोधा",
    "Save": "जतन करा",
    "Cancel": "रद्द करा",
    "Submit": "सबमिट करा",
    "Filter": "फिल्टर",
    "Service Provider": "सेवा प्रदाता",
    "Service Required": "सेवेची आवश्यकता",
    "Rate Per Hour": "प्रति तास दर",
    "Flat Visit Charge": "भेट शुल्क",
    "Dark Mode": "डार्क मोड",
    "Light Mode": "लाईट मोड",
    "Type your message...": "तुमचा संदेश टाइप करा...",
    "Write message...": "संदेश लिहा...",
    "Conversations": "संभाषणे",
    
    // Service Request Form Terms
    "Request a Service": "सेवेची विनंती करा",
    "Fill in your requirements to find a suitable service provider.": "योग्य सेवा प्रदाता शोधण्यासाठी आपल्या आवश्यकता भरा.",
    "Select Service Category": "सेवा श्रेणी निवडा",
    "Plumbing": "प्लंबिंग",
    "Required Service": "आवश्यक सेवा",
    "Your Full Name": "तुमचे पूर्ण नाव",
    "Mobile Number": "मोबाईल नंबर",
    "Service Location": "सेवेचे ठिकाण",
    "Preferred Service Date": "पसंतीची सेवा तारीख",
    "Choose date": "तारीख निवडा",
    "Expected Budget": "अपेक्षित बजेट",
    "Below ₹500": "₹५०० पेक्षा कमी",
    "₹500–₹1,000": "₹५००–₹१,०००",
    "₹1,000–₹5,000": "₹१,०००–₹५,०००",
    "Above ₹5,000": "₹५,००० पेक्षा जास्त",
    "Need provider quotation": "प्रदाता कोटेशन आवश्यक आहे",
    "How urgently do you need the service?": "तुम्हाला सेवेची किती तातडीची गरज आहे?",
    "Emergency": "इमर्जन्सी / तातडीचे",
    "Within 24 hours": "२४ तासांच्या आत",
    "Normal": "सामान्य",
    "Flexible date": "लवचिक तारीख",
    "Describe Your Requirement": "तुमच्या आवश्यकतेचे वर्णन करा",
    "Submit Service Request": "सेवा विनंती सबमिट करा"
};

function initLanguageManager() {
    setupGoogleTranslateWidget();
    
    const savedLang = localStorage.getItem('smart-community-lang') || 'en';
    if (savedLang === 'mr') {
        applyMarathiLanguage(false);
    } else {
        applyEnglishLanguage(false);
    }
}

function setupGoogleTranslateWidget() {
    if (!document.getElementById('google_translate_element')) {
        const div = document.createElement('div');
        div.id = 'google_translate_element';
        div.style.display = 'none';
        document.body.appendChild(div);
    }

    if (!window.googleTranslateElementInit) {
        window.googleTranslateElementInit = function() {
            try {
                new google.translate.TranslateElement({
                    pageLanguage: 'en',
                    includedLanguages: 'en,mr',
                    autoDisplay: false
                }, 'google_translate_element');
            } catch (e) {
                console.log('Google Translate init note:', e);
            }
        };

        const script = document.createElement('script');
        script.src = 'https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
        script.async = true;
        document.head.appendChild(script);
    }
}

window.switchLanguage = function(lang) {
    if (lang === 'mr') {
        applyMarathiLanguage(true);
    } else {
        applyEnglishLanguage(true);
    }
};

function triggerGoogleTranslate(langCode) {
    const select = document.querySelector('.goog-te-combo');
    if (select) {
        select.value = langCode;
        select.dispatchEvent(new Event('change'));
    } else {
        document.cookie = `googtrans=/en/${langCode}; path=/;`;
        document.cookie = `googtrans=/en/${langCode}; path=/; domain=.${location.hostname};`;
    }
}

function applyMarathiLanguage(showToast = true) {
    localStorage.setItem('smart-community-lang', 'mr');
    
    document.querySelectorAll('.lang-btn').forEach(b => {
        b.classList.toggle('active', b.id.includes('Mr'));
    });

    triggerGoogleTranslate('mr');
    translateDOMToMarathi();

    const currentTheme = localStorage.getItem('smart-community-theme') || 'light';
    updateThemeButtonUI(currentTheme);

    if (showToast && window.showModernToast) {
        showModernToast('मराठी भाषा सक्रिय झाली 🇮🇳', 'gold');
    }
}

function applyEnglishLanguage(showToast = true) {
    localStorage.setItem('smart-community-lang', 'en');
    
    document.querySelectorAll('.lang-btn').forEach(b => {
        b.classList.toggle('active', b.id.includes('En'));
    });

    triggerGoogleTranslate('en');
    restoreDOMToEnglish();

    const currentTheme = localStorage.getItem('smart-community-theme') || 'light';
    updateThemeButtonUI(currentTheme);

    if (showToast && window.showModernToast) {
        showModernToast('Language switched to English 🇬🇧', 'gold');
    }
}

function translateDOMToMarathi() {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    let node;
    while ((node = walker.nextNode())) {
        const parent = node.parentElement;
        if (!parent || parent.tagName === 'SCRIPT' || parent.tagName === 'STYLE' || parent.closest('.top-utility-bar') || parent.closest('.floating-top-utility-bar')) {
            continue;
        }

        const trimmed = node.nodeValue.trim();
        if (MARATHI_DICTIONARY[trimmed]) {
            if (!node._originalEnglish) {
                node._originalEnglish = node.nodeValue;
            }
            node.nodeValue = node.nodeValue.replace(trimmed, MARATHI_DICTIONARY[trimmed]);
        }
    }
}

function restoreDOMToEnglish() {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    let node;
    while ((node = walker.nextNode())) {
        if (node._originalEnglish) {
            node.nodeValue = node._originalEnglish;
        }
    }
}

/* ==========================================================================
   10. TOP-RIGHT UTILITY TOOLBAR MOUNTER
   ========================================================================== */
function initTopRightUtilityBar() {
    if (document.getElementById('topUtilityBar') || document.getElementById('floatingTopUtilityBar')) {
        return;
    }

    const currentLang = localStorage.getItem('smart-community-lang') || 'en';
    const currentTheme = localStorage.getItem('smart-community-theme') || 'light';
    const isDark = currentTheme === 'dark';

    const barHtml = `
        <div class="top-utility-bar" id="topUtilityBar">
            <div class="lang-switch-group" title="Language / भाषा">
                <button type="button" class="lang-btn ${currentLang === 'en' ? 'active' : ''}" id="btnLangEn" onclick="switchLanguage('en')">
                    <span>🇬🇧</span> EN
                </button>
                <button type="button" class="lang-btn ${currentLang === 'mr' ? 'active' : ''}" id="btnLangMr" onclick="switchLanguage('mr')">
                    <span>🇮🇳</span> मराठी
                </button>
            </div>
            <button type="button" class="theme-toggle-btn" id="themeToggleBtn" onclick="toggleAppTheme()" title="${isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}">
                <span class="theme-icon">${isDark ? '☀️' : '🌙'}</span>
                <span class="theme-text">${isDark ? (currentLang === 'mr' ? 'लाईट' : 'Light') : (currentLang === 'mr' ? 'डार्क' : 'Dark')}</span>
            </button>
        </div>
    `;

    // 1. Dashboard Top User Bar
    const topUserBar = document.querySelector('.top-user-bar');
    if (topUserBar) {
        const wrapper = document.createElement('div');
        wrapper.innerHTML = barHtml;
        const rightContainer = topUserBar.querySelector('div:last-child');
        if (rightContainer) {
            rightContainer.prepend(wrapper.firstElementChild);
        } else {
            topUserBar.appendChild(wrapper.firstElementChild);
        }
        return;
    }

    // 2. Base.html Portal Header
    const portalHeader = document.querySelector('.portal-header .header-user-badge') || document.querySelector('.portal-header');
    if (portalHeader) {
        const wrapper = document.createElement('div');
        wrapper.innerHTML = barHtml;
        portalHeader.prepend(wrapper.firstElementChild);
        return;
    }

    // 3. Main Landing Header
    const navContainer = document.querySelector('header .nav-container .nav-links') || document.querySelector('header .nav-container');
    if (navContainer) {
        const wrapper = document.createElement('li');
        wrapper.style.listStyle = 'none';
        wrapper.innerHTML = barHtml;
        navContainer.appendChild(wrapper);
        return;
    }

    // 4. Standalone Floating Top-Right (Login, Register, OTP, etc.)
    const floatingDiv = document.createElement('div');
    floatingDiv.id = 'floatingTopUtilityBar';
    floatingDiv.className = 'floating-top-utility-bar';
    floatingDiv.innerHTML = barHtml;
    document.body.appendChild(floatingDiv);
}
