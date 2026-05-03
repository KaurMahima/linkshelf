function setupResourceFilters() {
  const tables = document.querySelectorAll("[data-resource-table]");

  tables.forEach((table) => {
    const scope = table.closest("[data-resource-scope]");
    if (!scope) {
      return;
    }

    const searchInput = scope.querySelector("[data-search]");
    const filterButtons = scope.querySelectorAll("[data-filter]");
    const rows = table.querySelectorAll("[data-resource-row]");
    const emptyState = scope.querySelector("[data-empty-state]");
    let activeFilter = "All";

    function updateRows() {
      const query = searchInput ? searchInput.value.trim().toLowerCase() : "";
      let visibleCount = 0;

      rows.forEach((row) => {
        const matchesSearch = row.dataset.search.includes(query);
        const matchesFilter =
          activeFilter === "All" || row.dataset.category === activeFilter;
        const isVisible = matchesSearch && matchesFilter;

        row.hidden = !isVisible;
        if (isVisible) {
          visibleCount += 1;
        }
      });

      if (emptyState) {
        emptyState.hidden = visibleCount !== 0;
      }
    }

    if (searchInput) {
      searchInput.addEventListener("input", updateRows);
    }

    filterButtons.forEach((button) => {
      button.addEventListener("click", () => {
        activeFilter = button.dataset.filter;
        filterButtons.forEach((item) => {
          item.classList.toggle("is-active", item === button);
        });
        updateRows();
      });
    });

    updateRows();
  });
}

document.addEventListener("DOMContentLoaded", setupResourceFilters);
