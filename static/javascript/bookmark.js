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
    if (event) event.stopPropagation();

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

    // Check which folders already have this recipe bookmarked
    const bookmarkedFolders = [];
    for (const folder of userFolders) {
        try {
            const res = await fetch(`/api/folders/${folder.id}/bookmarks`);
            if (res.ok) {
                const bookmarks = await res.json();
                const alreadyBookmarked = bookmarks.some(b => b.recipe_id === recipeId);
                if (alreadyBookmarked) {
                    bookmarkedFolders.push(folder.name);
                }
            }
        } catch (err) {
            console.error('Failed to check folder bookmarks:', err);
        }
    }

    // Build folder select options, disabling already bookmarked folders
    let folderOptionsHTML = '<option value="">Select a folder...</option>';
    folderOptionsHTML += userFolders.map(f => {
        const isBookmarked = bookmarkedFolders.includes(f.name);
        const disabledAttr = isBookmarked ? 'disabled' : '';
        const bookmarkedLabel = isBookmarked ? ' (already bookmarked)' : '';
        return `<option value="${f.id}" ${disabledAttr}>${f.icon} ${escapeHtml(f.name)}${bookmarkedLabel}</option>`;
    }).join('');

    folderSelect.innerHTML = folderOptionsHTML;

    document.getElementById('bookmarkRecipeName').textContent = recipeName;
    document.getElementById('bookmarkError').classList.remove('show');

    // Show info about already bookmarked folders
    if (bookmarkedFolders.length > 0) {
        const infoDiv = document.getElementById('bookmarkInfo');
        if (infoDiv) {
            infoDiv.innerHTML = `⚠️ Already in: ${bookmarkedFolders.map(name => `<strong>${escapeHtml(name)}</strong>`).join(', ')}`;
            infoDiv.style.display = 'block';
        }
    } else {
        const infoDiv = document.getElementById('bookmarkInfo');
        if (infoDiv) {
            infoDiv.style.display = 'none';
        }
    }

    modal.style.display = 'flex';
}

function closeBookmarkModal() {
    document.getElementById('bookmarkModal').style.display = 'none';
    resetRating();
    // Hide info message
    const infoDiv = document.getElementById('bookmarkInfo');
    if (infoDiv) {
        infoDiv.style.display = 'none';
    }
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

            // Refresh search results if on search page to update bookmark status
            const searchInput = document.getElementById('headerSearchInput');
            if (searchInput && searchInput.value) {
                executeSearch(searchInput.value);
            }

            // Refresh bookmarks if on bookmarks page
            if (typeof loadBookmarks === 'function') {
                loadBookmarks();
            }
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
