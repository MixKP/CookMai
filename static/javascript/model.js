function formatDuration(isoDuration) {
    if (!isoDuration || isoDuration === '—') return '—';

    // Match PT5M, PT1H30M, PT30M, etc.
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

function openModal(recipe) {
    document.getElementById('modalTitle').textContent = recipe.Name;
    document.getElementById('modalImg').src = getImage(recipe.Images);

    // Description
    const desc = document.getElementById('modalDescription');
    desc.textContent = recipe.Description || 'No description available.';

    // Category
    document.getElementById('modalCategory').textContent = recipe.RecipeCategory || '—';

    // Times - Convert to user-friendly format
    document.getElementById('modalPrepTime').textContent = formatDuration(recipe.PrepTime);
    document.getElementById('modalCookTime').textContent = formatDuration(recipe.CookTime);
    document.getElementById('modalTotalTime').textContent = formatDuration(recipe.TotalTime);

    // Servings
    document.getElementById('modalServings').textContent = recipe.RecipeServings ? `${recipe.RecipeServings} people` : '—';

    // Rating
    const ratingContainer = document.getElementById('ratingContainer');
    const ratingEl = document.getElementById('modalRating');
    if (recipe.AggregatedRating && recipe.AggregatedRating > 0) {
        ratingEl.textContent = `⭐ ${recipe.AggregatedRating.toFixed(1)} (${recipe.ReviewCount || 0} reviews)`;
        ratingContainer.style.display = 'flex';
    } else {
        ratingContainer.style.display = 'none';
    }

    // Ingredients and Instructions
    document.getElementById('modalIngredients').innerHTML =
        parseArray(recipe.RecipeIngredientParts).map(i => `<li>${i}</li>`).join('') || '<li>—</li>';
    document.getElementById('modalInstructions').innerHTML =
        parseArray(recipe.RecipeInstructions).map(s => `<li>${s}</li>`).join('') || '<li>—</li>';

    document.getElementById('recipeModal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('recipeModal').style.display = 'none';
}

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeModal();
});

document.getElementById('recipeModal').addEventListener('click', e => {
    if (e.target.id === 'recipeModal') closeModal();
});