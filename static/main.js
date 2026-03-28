const CARDS_PER_ROW = 3;   // 3 columns in the grid
const ROWS_PER_PAGE = 2;   // show 2 rows at a time
const CARDS_PER_PAGE = CARDS_PER_ROW * ROWS_PER_PAGE; // = 6

let allArticles = [];      // full dataset from API
let visibleCount = CARDS_PER_PAGE; // how many cards are currently shown

// 1. FETCH NEWS (INITIAL LOAD)
async function loadNews() {
    try {
        const response = await fetch('/api/news');
        const data = await response.json();
        allArticles = data;
        visibleCount = CARDS_PER_PAGE;
        renderNews();
    } catch (error) {
        console.error("Failed to load news:", error);
    }
}

// 2. RENDER only the visible slice of allArticles
function renderNews() {
    const grid = document.getElementById('news-grid');
    const countEl = document.getElementById('news-count');
    const controls = document.getElementById('pagination-controls');
    const showMoreBtn = document.getElementById('show-more-btn');
    const showLessBtn = document.getElementById('show-less-btn');

    const slice = allArticles.slice(0, visibleCount);

    grid.innerHTML = '';
    slice.forEach((article, index) => {
        const card = document.createElement('div');
        card.className = 'bg-slate-800/40 border border-slate-700/50 p-6 rounded-2xl hover:border-blue-500/50 transition-all duration-300 hover:-translate-y-1 group card-enter';
        card.style.animationDelay = `${index * 40}ms`;
        card.innerHTML = `
            <div class="flex justify-between items-start mb-4">
                <span class="text-[10px] uppercase tracking-widest font-bold text-blue-400 bg-blue-400/10 px-2 py-1 rounded">${article.source}</span>
                <div class="flex items-center gap-1 text-amber-400 font-bold">
                    <i class="fas fa-fire-alt text-xs"></i>
                    <span>${article.impact_score}</span>
                </div>
            </div>
            <h3 class="text-lg font-bold text-white mb-3 leading-snug group-hover:text-blue-400 transition-colors">
                ${article.title}
            </h3>
            <p class="text-slate-400 text-sm line-clamp-3 mb-6">${article.summary}</p>
            <div class="flex justify-between items-center">
                <span class="text-xs text-slate-500">${new Date(article.published).toLocaleDateString()}</span>
                <a href="${article.link}" target="_blank" class="text-blue-500 hover:text-blue-400 text-sm font-bold flex items-center gap-1">
                    Source <i class="fas fa-arrow-right text-[10px]"></i>
                </a>
            </div>
        `;
        grid.appendChild(card);
    });

    // Update count label
    countEl.textContent = `Showing ${slice.length} of ${allArticles.length} articles`;

    // Show/hide pagination controls
    const hasMore = visibleCount < allArticles.length;
    const hasLess = visibleCount > CARDS_PER_PAGE;

    controls.classList.toggle('hidden', !hasMore && !hasLess);
    showMoreBtn.classList.toggle('hidden', !hasMore);
    showLessBtn.classList.toggle('hidden', !hasLess);
}

// 3. SHOW MORE — reveal next 2 rows
function showMore() {
    visibleCount = Math.min(visibleCount + CARDS_PER_PAGE, allArticles.length);
    renderNews();
    // Scroll down slightly so user sees the new cards
    window.scrollBy({ top: 300, behavior: 'smooth' });
}

// 4. SHOW LESS — collapse back by 2 rows (min = initial page)
function showLess() {
    visibleCount = Math.max(visibleCount - CARDS_PER_PAGE, CARDS_PER_PAGE);
    renderNews();
    // Scroll up a bit so user sees the top of the grid
    document.getElementById('news-grid').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// 5. SYNC NEWS
async function syncData() {
    const btn = document.getElementById('sync-icon');
    btn.classList.add('fa-spin');
    await fetch('/sync-news');
    await loadNews();
    btn.classList.remove('fa-spin');
}

// 6. AI ASK LOGIC (RAG)
async function askAI() {
    const queryInput = document.getElementById('ai-query');
    const responseBox = document.getElementById('ai-response-box');
    const answerText = document.getElementById('ai-answer-text');

    if (!queryInput.value) return;

    responseBox.classList.remove('hidden');
    answerText.innerHTML = `<span class="animate-pulse text-slate-500">Analyzing your feed with Mistral AI...</span>`;

    try {
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: queryInput.value })
        });

        const data = await response.json();
        answerText.classList.remove('italic');
        answerText.innerText = data.answer;
    } catch (error) {
        answerText.innerText = "Error: Make sure your Flask server and Ollama (Mistral) are running!";
    }
}

// Run on load
loadNews();
