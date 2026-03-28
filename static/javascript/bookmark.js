function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

let userFolders = [];
let currentRecipeId = null;
let currentRecipeName = null;

async function loadUserFolders() {
    try {
        const res = await fetch('/api/folders');
        userFolders = await res.json();
    } catch (err) {
        console.error('Failed to load folders:', err);
    }
}

async function openBookmarkModal(event, recipeId, recipeName) {
    event.stopPropagation();

    await loadUserFolders();

    if (userFolders.length === 0) {
        showToast('Please create a folder first!', 'error');
        setTimeout(() => {
            window.location.href = '/folders';
        }, 1500);
        return;
    }

    currentRecipeId = recipeId;
    currentRecipeName = recipeName;

    const modal = document.getElementById('bookmarkModal');
    const folderSelect = document.getElementById('bookmarkFolderSelect');

    folderSelect.innerHTML = '<option value="">Select a folder...</option>' +
        userFolders.map(f => `<option value="${f.id}">${f.icon} ${escapeHtml(f.name)}</option>`).join('');

    document.getElementById('bookmarkRecipeName').textContent = recipeName;
    document.getElementById('bookmarkError').classList.remove('show');

    modal.style.display = 'flex';
}

function closeBookmarkModal() {
    document.getElementById('bookmarkModal').style.display = 'none';
    resetRating();
}

function resetRating() {
    currentRating = 0;
    const wrappers = document.querySelectorAll('.star-rating .star-wrapper');
    wrappers.forEach(wrapper => {
        const star = wrapper.querySelector('.star');
        star.classList.remove('filled', 'half');
        star.textContent = '☆';
    });
    document.getElementById('bookmarkRating').value = '0';
    updateRatingLabel(0);
}

function setRating(rating) {
    currentRating = rating;
    document.getElementById('bookmarkRating').value = rating;
    updateRatingLabel(rating);

    const wrappers = document.querySelectorAll('.star-rating .star-wrapper');
    wrappers.forEach((wrapper, index) => {
        const starNumber = index + 1;
        const star = wrapper.querySelector('.star');

        star.classList.remove('filled', 'half');

        if (rating >= starNumber) {
            star.classList.add('filled');
            star.textContent = '★';
        } else if (rating >= starNumber - 0.5) {
            star.classList.add('half');
            star.textContent = '★';
        } else {
            star.textContent = '☆';
        }
    });
}

function updateRatingLabel(rating) {
    const labelEl = document.getElementById('ratingLabel');
    if (labelEl) {
        if (rating === 0) {
            labelEl.textContent = 'Select a rating';
        } else {
            labelEl.textContent = `${rating} / 5`;
        }
    }
}

let currentRating = 0;

function handleStarHover(event, starNumber) {
    const wrapper = event.currentTarget;
    const rect = wrapper.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const isLeftHalf = x < rect.width / 2;

    const rating = isLeftHalf ? starNumber - 0.5 : starNumber;
    previewRating(rating);
}

function setRatingFromClick(event, starNumber) {
    const wrapper = event.currentTarget;
    const rect = wrapper.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const isLeftHalf = x < rect.width / 2;

    const rating = isLeftHalf ? starNumber - 0.5 : starNumber;
    setRating(rating);
}

function previewRating(rating) {
    const wrappers = document.querySelectorAll('.star-rating .star-wrapper');
    wrappers.forEach((wrapper, index) => {
        const starNumber = index + 1;
        const star = wrapper.querySelector('.star');

        star.classList.remove('filled', 'half');

        if (rating >= starNumber) {
            star.classList.add('filled');
            star.textContent = '★';
        } else if (rating >= starNumber - 0.5) {
            star.classList.add('half');
            star.textContent = '★';
        } else {
            star.textContent = '☆';
        }
    });

    const labelEl = document.getElementById('ratingLabel');
    if (labelEl) {
        updateRatingLabel(rating);
    }
}

function resetPreview() {
    setRating(currentRating);
}

async function saveBookmark(event) {
    event.preventDefault();
    const folderId = document.getElementById('bookmarkFolderSelect').value;
    const rating = document.getElementById('bookmarkRating').value;
    const errorDiv = document.getElementById('bookmarkError');

    if (!folderId) {
        errorDiv.textContent = 'Please select a folder';
        errorDiv.classList.add('show');
        return;
    }

    if (parseFloat(rating) < 0.5) {
        errorDiv.textContent = 'Please select a rating';
        errorDiv.classList.add('show');
        return;
    }

    const data = {
        folder_id: parseInt(folderId),
        recipe_id: currentRecipeId,
        recipe_name: currentRecipeName,
        user_rating: parseFloat(rating)
    };

    try {
        const res = await fetch('/api/bookmarks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await res.json();

        if (res.ok) {
            closeBookmarkModal();
            showToast('Recipe bookmarked successfully! ✓', 'success');
        } else {
            errorDiv.textContent = result.error || 'Failed to save bookmark';
            errorDiv.classList.add('show');
            showToast(result.error || 'Failed to save bookmark', 'error');
        }
    } catch (err) {
        errorDiv.textContent = 'Network error. Please try again.';
        errorDiv.classList.add('show');
        showToast('Network error. Please try again.', 'error');
    }
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

document.getElementById('bookmarkModal').addEventListener('click', e => {
    if (e.target.id === 'bookmarkModal') closeBookmarkModal();
});
