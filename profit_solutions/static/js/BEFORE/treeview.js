document.addEventListener('DOMContentLoaded', function () {
    const tree = document.getElementById('account-tree');
    tree.addEventListener('click', function (event) {
      if (event.target.tagName === 'LI') {
        event.target.classList.toggle('expanded');
        
        // Toggle the visibility of immediate children
        const children = event.target.querySelector('ul');
        if (children) {
          children.style.display = children.style.display === 'none' ? 'block' : 'none';
        }
        
        // Hide the grandchildren
        const grandchildren = event.target.querySelectorAll('.grandchildren ul');
        grandchildren.forEach(grandchild => {
          grandchild.style.display = 'none';
        });
      }
    });
  });
  
  
  document.querySelector("form").addEventListener("submit", function (event) {
    if (!confirm("Are you sure you want to delete this item?")) {
        event.preventDefault();
    }
  });