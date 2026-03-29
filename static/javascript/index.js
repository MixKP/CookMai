let categoriesLoaded = false;

async function loadRecommendations() {
    try {
        // Load categories only once
        if (!categoriesLoaded) {
            await loadCategories();
            categoriesLoaded = true;
        }

        // Load recommendations
        const categorySelect = document.getElementById('categorySelect');
        const selectedCategory = categorySelect ? categorySelect.value : '';
        const url = selectedCategory ? `/api/recommendations?category=${encodeURIComponent(selectedCategory)}` : '/api/recommendations';

        const res = await fetch(url);
        const data = await res.json();

        const recommendationsSection = document.getElementById('recommendationsSection');
        const noBookmarksMessage = document.getElementById('noBookmarksMessage');

        // Check if user has any bookmarks
        if (!data.from_bookmarks || data.from_bookmarks.length === 0) {
            recommendationsSection.style.display = 'none';
            noBookmarksMessage.style.display = 'block';
            return;
        }

        recommendationsSection.style.display = 'block';
        noBookmarksMessage.style.display = 'none';

        // Render From Your Bookmarks
        if (data.from_bookmarks && data.from_bookmarks.length > 0) {
            renderRecommendationCards('bookmarksGrid', data.from_bookmarks, true);
            document.getElementById('bookmarksBlock').style.display = 'block';
        }

        // Render Category Picks
        if (data.category_picks && data.category_picks.length > 0) {
            renderRecommendationCards('categoryGrid', data.category_picks, false);
            document.getElementById('categoryBlock').style.display = 'block';
        }

        // Render Random Discoveries
        if (data.random_discoveries && data.random_discoveries.length > 0) {
            renderRecommendationCards('discoveriesGrid', data.random_discoveries, false);
            document.getElementById('discoveriesBlock').style.display = 'block';
        }

    } catch (err) {
        console.error('Failed to load recommendations:', err);
    }
}

async function loadCategories() {
    try {
        // Fetch all categories from the entire database
        const res = await fetch('/api/categories/all');
        const data = await res.json();

        const categorySelect = document.getElementById('categorySelect');
        if (!categorySelect) return;

        // Save the currently selected value
        const currentValue = categorySelect.value;

        // Clear existing options (keep the first one)
        categorySelect.innerHTML = '<option value="">All Categories (Random)</option>';

        // Add category options
        if (data.categories && data.categories.length > 0) {
            data.categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category;
                categorySelect.appendChild(option);
            });
        }

        // Restore the selected value if it still exists
        if (currentValue) {
            categorySelect.value = currentValue;
        }

        // Add event listener for category selection (only once)
        if (!categorySelect.hasAttribute('data-listener-added')) {
            categorySelect.addEventListener('change', onCategoryChange);
            categorySelect.setAttribute('data-listener-added', 'true');
        }

    } catch (err) {
        console.error('Failed to load categories:', err);
    }
}

function onCategoryChange() {
    // Reload recommendations when category changes
    loadRecommendations();
}

function renderRecommendationCards(containerId, recipes, showFolderInfo) {
    const container = document.getElementById(containerId);
    container.innerHTML = recipes.map((recipe, i) => {
        const imageSrc = recipe.image || 'https://upload.wikimedia.org/wikipedia/commons/1/14/No_Image_Available.jpg';
        const ratingBadge = recipe.rating
            ? `<span class="card-rating">⭐ ${recipe.rating.toFixed(1)}</span>`
            : '';

        const folderInfo = showFolderInfo && recipe.folder_name
            ? `<span class="card-folder">📁 ${escapeHtml(recipe.folder_name)}</span>`
            : '';

        const userRatingBadge = showFolderInfo && recipe.user_rating
            ? `<span class="card-user-rating">⭐ Your rating: ${recipe.user_rating}</span>`
            : '';

        return `
            <div class="recipe-card" onclick="viewRecipe(${recipe.recipe_id})" style="animation-delay: ${i * 50}ms">
                <div class="card-image">
                    <img src="${imageSrc}" alt="${escapeHtml(recipe.recipe_name)}" loading="lazy">
                    <div class="card-overlay">
                        ${ratingBadge}
                    </div>
                </div>
                <div class="card-content">
                    <h3 class="card-title">${escapeHtml(recipe.recipe_name)}</h3>
                    <div class="card-meta">
                        ${recipe.category && recipe.category !== '—' ? `<span class="card-category">${escapeHtml(recipe.category)}</span>` : ''}
                        ${folderInfo}
                    </div>
                    ${userRatingBadge}
                </div>
            </div>
        `;
    }).join('');
}

async function viewRecipe(recipeId) {
    try {
        // Check if recipe is already bookmarked
        let isBookmarked = false;
        try {
            const bookmarksRes = await fetch('/api/bookmarks/all');
            if (bookmarksRes.ok) {
                const bookmarks = await bookmarksRes.json();
                isBookmarked = bookmarks.some(b => b.recipe_id === recipeId);
            }
        } catch (err) {
            console.error('Failed to check bookmark status:', err);
        }

        // Fetch recipe details
        const res = await fetch(`/api/recipes/${recipeId}`);
        if (!res.ok) {
            throw new Error('Failed to fetch recipe details');
        }
        const recipe = await res.json();

        // Open modal with bookmark status
        openModal(recipe, isBookmarked);
    } catch (err) {
        console.error('Failed to load recipe:', err);
        showToast('Failed to load recipe details', 'error');
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

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Load recommendations when page loads
document.addEventListener('DOMContentLoaded', () => {
    loadRecommendations();
});
