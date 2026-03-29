function openModal(recipe, isBookmarked = false) {
    document.getElementById('modalTitle').textContent = recipe.Name;
    document.getElementById('modalImg').src = getImage(recipe.Images);

    const desc = document.getElementById('modalDescription');
    const description = recipe.Description;
    if (description && description !== 'Make and share this ' + recipe.Name + ' recipe from Food.com.') {
        desc.textContent = description;
        desc.style.display = 'block';
    } else {
        desc.style.display = 'none';
    }

    const category = recipe.RecipeCategory;
    document.getElementById('modalCategory').textContent = category || '—';

    document.getElementById('modalPrepTime').textContent = formatDuration(recipe.PrepTime);
    document.getElementById('modalCookTime').textContent = formatDuration(recipe.CookTime);
    document.getElementById('modalTotalTime').textContent = formatDuration(recipe.TotalTime);

    document.getElementById('modalServings').textContent = recipe.RecipeServings || '—';

    const ratingContainer = document.getElementById('ratingContainer');
    const ratingEl = document.getElementById('modalRating');
    if (recipe.AggregatedRating && recipe.AggregatedRating > 0) {
        ratingEl.textContent = `⭐ ${recipe.AggregatedRating.toFixed(1)} (${recipe.ReviewCount || 0} reviews)`;
        ratingContainer.style.display = 'flex';
    } else {
        ratingContainer.style.display = 'none';
    }

    const ingredients = parseArray(recipe.RecipeIngredientParts);
    if (ingredients.length > 0) {
        document.getElementById('modalIngredients').innerHTML = ingredients.map(i => `<li>${i}</li>`).join('');
    } else {
        document.getElementById('modalIngredients').innerHTML = '<li style="color: #999;">No ingredients listed</li>';
    }

    const instructions = parseArray(recipe.RecipeInstructions);
    if (instructions.length > 0) {
        document.getElementById('modalInstructions').innerHTML = instructions.map(s => `<li>${s}</li>`).join('');
    } else {
        document.getElementById('modalInstructions').innerHTML = '<li style="color: #999;">No instructions provided</li>';
    }

    const bookmarkBtn = document.getElementById('modalBookmarkBtn');

    if (isBookmarked) {
        bookmarkBtn.textContent = '✓ Already Bookmarked';
        bookmarkBtn.disabled = true;
        bookmarkBtn.style.background = '#d1fae5';
        bookmarkBtn.style.color = '#065f46';
        bookmarkBtn.style.borderColor = '#10b981';
        bookmarkBtn.style.cursor = 'not-allowed';
        bookmarkBtn.onclick = null;
    } else {
        bookmarkBtn.textContent = '🔖 Bookmark this Recipe';
        bookmarkBtn.disabled = false;
        bookmarkBtn.style.background = '';
        bookmarkBtn.style.color = '';
        bookmarkBtn.style.borderColor = '';
        bookmarkBtn.style.cursor = '';
            bookmarkBtn.onclick = (e) => openBookmarkModal(e, recipe.RecipeId, recipe.Name);
    }

    document.getElementById('recipeModal').style.display = 'flex';
}

function closeModal() {
    const bookmarkBtn = document.getElementById('modalBookmarkBtn');
    bookmarkBtn.textContent = '🔖 Bookmark this Recipe';
    bookmarkBtn.disabled = false;
    bookmarkBtn.style.background = '';
    bookmarkBtn.style.color = '';
    bookmarkBtn.style.borderColor = '';
    bookmarkBtn.style.cursor = '';
    bookmarkBtn.onclick = null;

    const bookmarkInfo = document.getElementById('alreadyBookmarkedInfo');
    if (bookmarkInfo) bookmarkInfo.remove();

    document.getElementById('recipeModal').style.display = 'none';
}

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeModal();
});

document.getElementById('recipeModal').addEventListener('click', e => {
    if (e.target.id === 'recipeModal') closeModal();
});
