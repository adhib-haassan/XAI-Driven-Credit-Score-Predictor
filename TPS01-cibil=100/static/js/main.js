// Main JavaScript file for the application

document.addEventListener('DOMContentLoaded', function() {
    // Add any global JavaScript functionality here
    
    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
    
    // Password confirmation validation
    const password = document.getElementById('password');
    const confirm_password = document.getElementById('confirm_password');
    
    if (password && confirm_password) {
        confirm_password.addEventListener('input', function() {
            if (password.value !== confirm_password.value) {
                confirm_password.setCustomValidity('Passwords do not match');
            } else {
                confirm_password.setCustomValidity('');
            }
        });
    }
});