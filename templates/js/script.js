document.addEventListener('DOMContentLoaded', function() {
    // Add subtle animation to login form
    const form = document.querySelector('form');
    if (form) {
        form.style.opacity = '0';
        form.style.transform = 'translateY(20px)';
        setTimeout(() => {
            form.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            form.style.opacity = '1';
            form.style.transform = 'translateY(0)';
        }, 300);
    }

    // Add hover effects to interactive elements
    const interactiveElements = document.querySelectorAll('a, button, input[type="checkbox"]');
    interactiveElements.forEach(el => {
        el.addEventListener('mouseenter', () => {
            el.style.transform = 'scale(1.02)';
        });
        el.addEventListener('mouseleave', () => {
            el.style.transform = 'scale(1)';
        });
    });

    // Password visibility toggle (would need additional HTML element)
    const passwordInput = document.querySelector('input[type="password"]');
    if (passwordInput) {
        const passwordContainer = passwordInput.parentElement;
        const toggle = document.createElement('span');
        toggle.innerHTML = '<i data-feather="eye" class="w-4 h-4 absolute right-3 top-1/2 transform -translate-y-1/2 cursor-pointer text-slate-400 hover:text-indigo-600"></i>';
        toggle.classList.add('password-toggle');
        passwordContainer.style.position = 'relative';
        passwordContainer.appendChild(toggle);
        
        toggle.addEventListener('click', function() {
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                toggle.innerHTML = '<i data-feather="eye-off" class="w-4 h-4 absolute right-3 top-1/2 transform -translate-y-1/2 cursor-pointer text-indigo-600"></i>';
            } else {
                passwordInput.type = 'password';
                toggle.innerHTML = '<i data-feather="eye" class="w-4 h-4 absolute right-3 top-1/2 transform -translate-y-1/2 cursor-pointer text-slate-400 hover:text-indigo-600"></i>';
            }
            feather.replace();
        });
    }

    feather.replace();
});