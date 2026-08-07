const input = document.getElementById("search-input");
const results = document.getElementById("search-results");

if (input && results) {

    let timeout;

    input.addEventListener("input", function () {

        clearTimeout(timeout);

        const q = this.value.trim();

        if (q.length < 1) {

            results.classList.add("d-none");
            results.innerHTML = "";

            return;

        }

        results.classList.remove("d-none");

        results.innerHTML = `
            <div class="search-loading">
                Searching...
            </div>
        `;

        timeout = setTimeout(() => {

            fetch(`/search/ajax/?q=${encodeURIComponent(q)}`)

                .then(r => r.json())

                .then(data => {

                    buildSearch(data, q);

                });

        }, 200);

    });

    document.addEventListener("click", function (e) {

        if (!e.target.closest(".search-wrapper")) {

            results.classList.add("d-none");

        }

    });

}



function tournamentCard(t) {

    return `

    <a href="${t.url}" class="search-card">

        <div class="search-card-header">

            <div>

                <div class="search-title">

                    ${t.name}

                </div>

                <div class="search-game">

                    🎮 ${t.game}

                </div>

            </div>

            <span class="badge bg-primary">

                ${t.status}

            </span>

        </div>

        <div class="search-info">

            <div>

                💰

                NPR ${Number(t.prize_pool).toLocaleString()}

            </div>

            <div>

                📅

                ${t.start_date}

            </div>

            <div>

                📝

                ${t.registration_end}

            </div>

        </div>

    </a>

    `;

}



function gameCard(g) {

    return `

    <div class="search-card">

        <div class="search-title">

            🎮 ${g.name}

        </div>

        <div class="search-game">

            ${g.tournaments} tournaments

        </div>

    </div>

    `;

}



function teamCard(team) {

    return `

    <a href="${team.url}" class="search-card">

        <div class="search-title">

            👥 ${team.name}

        </div>

        <div class="search-game">

            Manager : ${team.manager}

        </div>

    </a>

    `;

}



function buildSearch(data, q) {

    let html = "";

    if (data.tournaments.length) {

        html += `

        <div class="search-section">

            <div class="search-heading">

                🏆 TOURNAMENTS

            </div>

        `;

        data.tournaments.forEach(t => {

            html += tournamentCard(t);

        });

        html += "</div>";

    }



    if (data.games.length) {

        html += `

        <div class="search-section">

            <div class="search-heading">

                🎮 GAMES

            </div>

        `;

        data.games.forEach(g => {

            html += gameCard(g);

        });

        html += "</div>";

    }



    if (data.teams.length) {

        html += `

        <div class="search-section">

            <div class="search-heading">

                👥 TEAMS

            </div>

        `;

        data.teams.forEach(team => {

            html += teamCard(team);

        });

        html += "</div>";

    }



    if (html === "") {

        html = `

        <div class="search-empty">

            No results found.

        </div>

        `;

    }



    html += `

    <a class="search-view-all"

       href="/search/?q=${encodeURIComponent(q)}">

        View all results →

    </a>

    `;



    results.innerHTML = html;

}