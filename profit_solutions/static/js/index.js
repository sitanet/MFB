// first table start here for deposit-----------------------------
function searchTable() {
  var input, filter, table, tr, td, i, txtValue;
  input = document.getElementById("searchInput");
  filter = input.value.toUpperCase();
  table = document.querySelector("table");
  tr = table.getElementsByTagName("tr");

  for (i = 0; i < tr.length; i++) {
    td = tr[i].getElementsByTagName("td");
    for (var j = 0; j < td.length; j++) {
      if (td[j]) {
        txtValue = td[j].textContent || td[j].innerText;
        if (txtValue.toUpperCase().indexOf(filter) > -1) {
          tr[i].style.display = "";
          break; // Show the row if any of its cells match the search query
        } else {
          tr[i].style.display = "none"; // Hide the row if none of its cells match the search query
        }
      }
    }
  }
}

function showForm(button) {
  // Get a reference to the form and the table
  const form = document.getElementById("depositForm");
  const table = document.querySelector(".table-row1");

  // Get the parent row of the clicked button
  const row = button.parentNode.parentNode;

  // Extract the information from the row
  const firstName = row.cells[1].textContent;
  const lastName = row.cells[2].textContent;
  const glNo = row.cells[3].textContent;
  const accountNo = row.cells[4].textContent;

  // Update the form inputs with the extracted information
  const selectedRow = document.getElementById("selectedRow");
  selectedRow.textContent = `${firstName} ${lastName}`;
  document.getElementById("glNoInput1").value = glNo;
  document.getElementById("accountNoInput1").value = accountNo;

  // Show the form
  form.style.display = "block";

  // Hide the table
  table.style.display = "none";
}
// first table end here for deposit-----------------------------

// Second table start here for deposit---------------------------------------

function updateForm(button) {
  const form = document.getElementById("depositForm");
  const table = document.querySelector(".table-row1");

  // Get the parent row of the clicked button
  const row = button.parentNode.parentNode;
  const glNo = row.cells[2].textContent;
  const accountNo = row.cells[3].textContent;

  document.getElementById("glNoInput2").value = glNo;
  document.getElementById("accountNoInput2").value = accountNo;
}

document.addEventListener("DOMContentLoaded", function () {
  const row1 = document.getElementById("row2");
  const showButton = document.getElementById("showButton");

  showButton.addEventListener("click", function () {
    if (row1.style.display === "none") {
      row1.style.display = "block"; // Show "row1"
    } else {
      row1.style.display = "none"; // Hide "row1"
    }
  });
});

// Function to search and filter Table 2
function searchTable2() {
  var input, filter, table, tr, td, i, j, txtValue;
  input = document.getElementById("searchInput2");
  filter = input.value.toLowerCase();
  table = document.querySelector("#row2 table"); // Get the table inside the row
  tr = table.getElementsByTagName("tr");

  for (i = 1; i < tr.length; i++) {
    // Start at 1 to skip the header row
    var visible = false; // Initialize visibility to false for each row
    td = tr[i].getElementsByTagName("td");

    for (j = 0; j < td.length; j++) {
      var cell = td[j];
      if (cell) {
        txtValue = cell.textContent || cell.innerText;
        if (txtValue.toLowerCase().indexOf(filter) > -1) {
          visible = true; // If the search term is found in any cell, set visibility to true
          break;
        }
      }
    }

    // Set the row's display style based on visibility
    tr[i].style.display = visible ? "" : "none";
  }
}
// Second table end here for deposit------------------------------------------



