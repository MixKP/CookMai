async function executeSearch(query) {
    if (!query.trim()) return;

    document.getElementById('resultsSection').style.display = 'block';
    document.getElementById('headerSearchInput').value = query;
    document.getElementById('queryLabel').textContent = `"${query}"`;
    document.getElementById('recipeList').innerHTML = '';
    document.getElementById('noResults').style.display = 'none';
    document.getElementById('typoAlert').style.display = 'none';
    document.getElementById('spinner').style.display = 'block';

    try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const data = await res.json();

        document.getElementById('spinner').style.display = 'none';

        if (data.error) {
            document.getElementById('noResults').style.display = 'block';
            document.getElementById('resultsCount').textContent = 'top 0 matches';
            return;
        }

        if (data.has_typo) {
            const alertBox = document.getElementById('typoAlert');
            const link = document.getElementById('suggestedLink');
            const keepLink = document.getElementById('keepOriginal');
            const originalQuerySpan = document.getElementById('originalQuery');

            link.textContent = data.suggested_query;
            link.onclick = (e) => {
                e.preventDefault();
                executeSearch(data.suggested_query);
            };

            originalQuerySpan.textContent = data.original_query;
            keepLink.onclick = (e) => {
                e.preventDefault();
                dismissAlert();
            };

            alertBox.style.display = 'flex';
        }

        const list = document.getElementById('recipeList');

        if (!data.results || data.results.length === 0) {
            document.getElementById('noResults').style.display = 'block';
            document.getElementById('resultsCount').textContent = 'top 0 matches';
            return;
        }

        document.getElementById('resultsCount').textContent = `top ${data.results.length} match${data.results.length !== 1 ? 'es' : ''}`;

        data.results.forEach((recipe, i) => {
            const ings = parseArray(recipe.RecipeIngredientParts);
            const ingPreview = ings.slice(0, 5).join(', ') + (ings.length > 5 ? '…' : '');

            const item = document.createElement('div');
            item.className = 'recipe-item';
            item.style.animationDelay = `${i * 40}ms`;
            item.onclick = () => openModal(recipe);
            item.innerHTML = `
                <img class="recipe-thumb" src="${getImage(recipe.Images)}" loading="lazy" alt="${recipe.Name}">
                <div class="recipe-info">
                    <div class="recipe-name">${recipe.Name}</div>
                    <div class="recipe-ingredients"><strong>Ingredients:</strong> ${ingPreview || '—'}</div>
                    <div class="recipe-meta">
                        ${recipe.AggregatedRating ? `<span class="badge-score">⭐ ${recipe.AggregatedRating.toFixed(1)} ${recipe.ReviewCount ? `(${recipe.ReviewCount})` : ''}</span>` : '<span class="badge-score">No ratings</span>'}
                        ${ings.length ? `<span class="badge-ingredients">${ings.length} ingredients</span>` : ''}
                    </div>
                    <button class="btn-bookmark" onclick="openBookmarkModal(event, ${recipe.RecipeId}, '${escapeHtml(recipe.Name)}')" title="Bookmark this recipe">
                        🔖 Bookmark
                    </button>
                </div>
            `;
            list.appendChild(item);
        });

    } catch (err) {
        document.getElementById('spinner').style.display = 'none';
        document.getElementById('noResults').style.display = 'block';
        console.error(err);
    }
}

function dismissAlert() {
    document.getElementById('typoAlert').style.display = 'none';
}

document.getElementById('headerSearchForm').addEventListener('submit', e => {
    e.preventDefault();
    executeSearch(document.getElementById('headerSearchInput').value);
});
