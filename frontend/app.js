/**
 * BarePage — Frontend JavaScript
 * Handles URL submission, API calls, freemium tracking, and displaying cleaned content.
 */

(function () {
    'use strict';

    const API_ENDPOINT = '/api/clean';
    const PREMIUM_LINK = 'https://buy.stripe.com/3cIdRb0Hq0lCd9Y4ZG00';
    const FREE_DAILY_LIMIT = 5;

    // ===== Freemium Utils =====
    function getUsage() {
        const raw = localStorage.getItem('barepage_usage');
        if (!raw) return { date: null, count: 0 };
        try { return JSON.parse(raw); } catch { return { date: null, count: 0 }; }
    }

    function setUsage(date, count) {
        localStorage.setItem('barepage_usage', JSON.stringify({ date, count }));
    }

    function isPremium() {
        return localStorage.getItem('barepage_premium') === 'true';
    }

    function getRemainingFree() {
        const usage = getUsage();
        const today = new Date().toISOString().split('T')[0];
        if (usage.date !== today) {
            setUsage(today, 0);
            return FREE_DAILY_LIMIT;
        }
        return Math.max(0, FREE_DAILY_LIMIT - usage.count);
    }

    function incrementUsage() {
        const usage = getUsage();
        const today = new Date().toISOString().split('T')[0];
        if (usage.date !== today) {
            setUsage(today, 1);
        } else {
            setUsage(today, usage.count + 1);
        }
    }

    function updateUsageUI() {
        const counter = document.getElementById('usage-counter');
        const premiumBadge = document.getElementById('premium-badge');
        const nonPremium = document.getElementById('non-premium');
        const premiumCta = document.getElementById('premium-cta');

        if (isPremium()) {
            if (premiumBadge) premiumBadge.classList.remove('hidden');
            if (nonPremium) nonPremium.classList.add('hidden');
            if (counter) counter.textContent = 'Unlimited';
            if (premiumCta) premiumCta.classList.add('hidden');
        } else {
            if (premiumBadge) premiumBadge.classList.add('hidden');
            if (nonPremium) nonPremium.classList.remove('hidden');
            const remaining = getRemainingFree();
            if (counter) counter.textContent = `${remaining} / ${FREE_DAILY_LIMIT}`;
            if (premiumCta) premiumCta.classList.remove('hidden');
            if (remaining <= 0) {
                showError(`You've used all ${FREE_DAILY_LIMIT} free cleanups today. Upgrade to Premium for unlimited use!`);
                return false;
            }
        }
        return true;
    }

    // ===== Pricing Modal =====
    function openPricing() {
        const modal = document.getElementById('pricing-modal');
        if (modal) modal.classList.remove('hidden');
    }

    function closePricing() {
        const modal = document.getElementById('pricing-modal');
        if (modal) modal.classList.add('hidden');
    }

    // ===== Core App =====
    const urlInput = document.getElementById('url-input');
    const btnBloat = document.getElementById('btn-bloat');
    const btnAds = document.getElementById('btn-ads');
    const loading = document.getElementById('loading');
    const errorBox = document.getElementById('error');
    const errorMessage = document.querySelector('.error-message');
    const dismissError = document.getElementById('dismiss-error');
    const results = document.getElementById('results');
    const resultTitle = document.getElementById('result-title');
    const resultMode = document.getElementById('result-mode');
    const viewOriginal = document.getElementById('view-original');
    const copyText = document.getElementById('copy-text');
    const backBtn = document.getElementById('back-btn');
    const contentDisplay = document.getElementById('content-display');

    let currentResult = null;

    function showLoading() {
        loading.classList.remove('hidden');
        errorBox.classList.add('hidden');
        results.classList.add('hidden');
    }

    function hideLoading() {
        loading.classList.add('hidden');
    }

    function showError(message) {
        errorBox.classList.remove('hidden');
        errorMessage.textContent = message || 'Something went wrong. Please try again.';
        hideLoading();
    }

    function getUrl() {
        let url = urlInput.value.trim();
        if (!url) {
            showError('Please enter a URL.');
            return null;
        }
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            url = 'https://' + url;
        }
        return url;
    }

    function isValidUrl(string) {
        try { new URL(string); return true; } catch { return false; }
    }

    async function cleanUrl(url, mode) {
        // Check free tier limit
        if (!isPremium() && getRemainingFree() <= 0) {
            openPricing();
            return;
        }

        showLoading();

        if (!isValidUrl(url)) {
            showError('The URL appears to be invalid. Please check it and try again.');
            return;
        }

        try {
            const response = await fetch(API_ENDPOINT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, mode }),
            });

            if (!response.ok) {
                const data = await response.json().catch(() => ({}));
                throw new Error(data.detail || `Server error (${response.status})`);
            }

            const result = await response.json();
            currentResult = result;
            if (!isPremium()) incrementUsage();
            updateUsageUI();
            displayResult(result);
        } catch (err) {
            showError(err.message || 'Failed to fetch or clean the URL. The page may be unreachable.');
        }
    }

    function displayResult(result) {
        hideLoading();
        errorBox.classList.add('hidden');

        resultTitle.textContent = result.title || 'Untitled Page';
        resultMode.textContent = result.mode === 'bloat' ? 'Bloat Removed' : 'Ads Removed';
        resultMode.setAttribute('data-mode', result.mode);
        viewOriginal.href = result.url;
        contentDisplay.innerHTML = result.content || '<p><em>No content could be extracted from this page.</em></p>';

        results.classList.remove('hidden');
        results.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function resetUI() {
        results.classList.add('hidden');
        errorBox.classList.add('hidden');
        hideLoading();
        currentResult = null;
        urlInput.focus();
    }

    async function copyCleanedText() {
        if (!currentResult) return;
        try {
            await navigator.clipboard.writeText(currentResult.content_text);
            copyText.textContent = '\u2713 Copied!';
            setTimeout(() => { copyText.innerHTML = '&#128203; Copy Text'; }, 2000);
        } catch {
            const textarea = document.createElement('textarea');
            textarea.value = currentResult.content_text;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            copyText.textContent = '\u2713 Copied!';
            setTimeout(() => { copyText.innerHTML = '&#128203; Copy Text'; }, 2000);
        }
    }

    // ===== Event Listeners =====
    btnBloat.addEventListener('click', function () {
        const url = getUrl();
        if (url) cleanUrl(url, 'bloat');
    });

    btnAds.addEventListener('click', function () {
        const url = getUrl();
        if (url) cleanUrl(url, 'ads');
    });

    urlInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const url = getUrl();
            if (url) cleanUrl(url, 'bloat');
        }
    });

    dismissError.addEventListener('click', function () {
        errorBox.classList.add('hidden');
    });

    backBtn.addEventListener('click', resetUI);
    copyText.addEventListener('click', copyCleanedText);

    // Pricing modal
    document.querySelectorAll('.pricing-close, .pricing-overlay').forEach(el => {
        el.addEventListener('click', closePricing);
    });
    document.querySelectorAll('.pricing-btn-upgrade').forEach(el => {
        el.addEventListener('click', function () { window.open(PREMIUM_LINK, '_blank'); });
    });
    document.querySelectorAll('.pricing-btn-open').forEach(el => {
        el.addEventListener('click', openPricing);
    });

    // Init
    updateUsageUI();
    urlInput.focus();
    console.log('BarePage loaded. Premium:', PREMIUM_LINK);
})();