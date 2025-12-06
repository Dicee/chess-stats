// this script is designed to run in the developer console of the browser, on page https://www.chess.com/openings after clicking "All openings"

const allOpenings = ["opening_name\topening_moves"]

function processPage(page) {
	console.log("Processing page", page, "...");
	const openings = document.getElementsByClassName("opening-component");
	for (let opening of openings) {
		const content = opening.getElementsByClassName("opening-content")[0];
		const name = content.getElementsByClassName("opening-name")[0].innerHTML;
		const moves = content.getElementsByClassName("opening-description")[0].innerHTML;
		if (name !== "Undefined") allOpenings.push(name + "\t" + moves);
	}

	page++;

	identifyPaginationButtons();
	const paginationButton = document.getElementById("page-" + page);
	
	if (paginationButton) {
		paginationButton.click();
		// just a precaution in case it takes some time to load the page, so that we don't inspect the DOM too early
		setTimeout(() => processPage(page), 1200);
	} else {
		console.log("Found", allOpenings.length - 1, "openings");
	}
}

function identifyPaginationButtons() {
	for (let button of document.querySelectorAll(".cc-pagination-button")) {
    	if (isNumeric(button.innerText)) button.id = "page-" + button.innerText;
	}	
}

function isNumeric(str) {
  if (typeof str != "string") return false
  return !isNaN(str) && !isNaN(parseInt(str))
}

processPage(1)
