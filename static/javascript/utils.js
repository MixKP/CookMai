const parseArray = (str) => {
    if (!str || str === 'character(0)') return [];
    try {
        let cleaned = str.replace(/^c\(/, '').replace(/\)$/, '');
        let matches = [...cleaned.matchAll(/"([^"]+)"|'([^']+)'/g)];
        return matches.map(m => m[1] || m[2]);
    } catch (e) { return [str]; }
};

const getImage = (str) => {
    if (str && str.startsWith('http')) return str;
    const arr = parseArray(str);
    if (arr.length && arr[0].startsWith('http')) return arr[0];
    return '/static/images/no-image.jpg';
};

function formatDuration(isoDuration) {
    if (!isoDuration || isoDuration === '—') return '—';
    const match = isoDuration.match(/PT(?:(\d+)H)?(?:(\d+)M)?/);
    if (!match) return '—';
    const hours = match[1] ? parseInt(match[1]) : 0;
    const minutes = match[2] ? parseInt(match[2]) : 0;
    if (hours === 0 && minutes === 0) return '—';
    const parts = [];
    if (hours > 0) {
        parts.push(`${hours} hr${hours > 1 ? 's' : ''}`);
    }
    if (minutes > 0) {
        parts.push(`${minutes} min${minutes > 1 ? 's' : ''}`);
    }
    return parts.join(' ');
}

function showToast(message, type = 'success') {
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span>${type === 'success' ? '✓' : '✕'}</span>
        <span>${message}</span>
    `;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('removing');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function checkBookmarkStatus(recipeId) {
    try {
        const bookmarksRes = await fetch('/api/bookmarks/all');
        if (bookmarksRes.ok) {
            const bookmarks = await bookmarksRes.json();
            return bookmarks.some(b => b.recipe_id === recipeId);
        }
    } catch (err) {
        console.error('Failed to check bookmark status:', err);
    }
    return false;
}

async function fetchRecipe(recipeId) {
    const res = await fetch(`/api/recipes/${recipeId}`);
    if (!res.ok) {
        throw new Error('Failed to fetch recipe details');
    }
    return await res.json();
}

async function fetchBookmarkedRecipeIds() {
    try {
        const bookmarksRes = await fetch('/api/bookmarks/all');
        if (bookmarksRes.ok) {
            const bookmarks = await bookmarksRes.json();
            return new Set(bookmarks.map(b => b.recipe_id));
        }
    } catch (err) {
        console.error('Failed to fetch bookmarks:', err);
    }
    return new Set();
}

async function checkAuth(redirectToLogin = true) {
    try {
        const res = await fetch('/api/auth/status');
        const data = await res.json();
        if (data.authenticated) {
            const usernameEl = document.getElementById('username');
            if (usernameEl) {
                usernameEl.textContent = data.username;
            }
            return data;
        } else if (redirectToLogin) {
            window.location.href = '/login';
        }
    } catch (err) {
        if (redirectToLogin) {
            window.location.href = '/login';
        }
    }
    return null;
}

async function handleLogout() {
    await fetch('/api/auth/logout', { method: 'POST' });
    window.location.href = '/login';
}

function renderStars(rating) {
    let stars = '';
    for (let i = 1; i <= 5; i++) {
        if (rating >= i) {
            stars += '<span class="star-filled">★</span>';
        } else if (rating >= i - 0.5) {
            stars += '<span class="star-half">★</span>';
        } else {
            stars += '<span class="star-empty">☆</span>';
        }
    }
    return stars;
}
