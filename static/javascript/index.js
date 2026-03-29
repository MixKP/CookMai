let categoriesLoaded = false;

async function loadRecommendations() {
    try {
        if (!categoriesLoaded) {
            await loadCategories();
            categoriesLoaded = true;
        }

        const categorySelect = document.getElementById('categorySelect');
        const selectedCategory = categorySelect ? categorySelect.value : '';
        const url = selectedCategory ? `/api/recommendations?category=${encodeURIComponent(selectedCategory)}` : '/api/recommendations';

        const res = await fetch(url);
        const data = await res.json();

        const recommendationsSection = document.getElementById('recommendationsSection');
        const noBookmarksMessage = document.getElementById('noBookmarksMessage');

        if (!data.from_bookmarks || data.from_bookmarks.length === 0) {
            recommendationsSection.style.display = 'none';
            noBookmarksMessage.style.display = 'block';
            return;
        }

        recommendationsSection.style.display = 'block';
        noBookmarksMessage.style.display = 'none';

        if (data.from_bookmarks && data.from_bookmarks.length > 0) {
            renderRecommendationCards('bookmarksGrid', data.from_bookmarks, true);
            document.getElementById('bookmarksBlock').style.display = 'block';
        }

        if (data.category_picks && data.category_picks.length > 0) {
            renderRecommendationCards('categoryGrid', data.category_picks, false);
            document.getElementById('categoryBlock').style.display = 'block';
        }

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
        const res = await fetch('/api/categories/all');
        const data = await res.json();

        const categorySelect = document.getElementById('categorySelect');
        if (!categorySelect) return;

        const currentValue = categorySelect.value;

        categorySelect.innerHTML = '<option value="">All Categories (Random)</option>';

        if (data.categories && data.categories.length > 0) {
            data.categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category;
                categorySelect.appendChild(option);
            });
        }

        if (currentValue) {
            categorySelect.value = currentValue;
        }

        if (!categorySelect.hasAttribute('data-listener-added')) {
            categorySelect.addEventListener('change', onCategoryChange);
            categorySelect.setAttribute('data-listener-added', 'true');
        }

    } catch (err) {
        console.error('Failed to load categories:', err);
    }
}

function onCategoryChange() {
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
        const isBookmarked = await checkBookmarkStatus(recipeId);
        const recipe = await fetchRecipe(recipeId);
        openModal(recipe, isBookmarked);
    } catch (err) {
        console.error('Failed to load recipe:', err);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadRecommendations();
});
