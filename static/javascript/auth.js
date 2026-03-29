function setButtonLoading(btn, isLoading) {
    const btnText = btn.querySelector('.btn-text');
    const btnSpinner = btn.querySelector('.btn-spinner');
    if (isLoading) {
        btn.disabled = true;
        btnText.style.display = 'none';
        btnSpinner.style.display = 'inline';
    } else {
        btn.disabled = false;
        btnText.style.display = 'inline';
        btnSpinner.style.display = 'none';
    }
}

function showError(errorDiv, message) {
    errorDiv.textContent = message;
    errorDiv.classList.add('show');
}

async function handleLogin(e) {
    e.preventDefault();
    const form = e.target;
    const btn = form.querySelector('button[type="submit"]');
    const errorDiv = document.getElementById('errorMessage');
    const username = form.username.value.trim();
    const password = form.password.value;

    errorDiv.classList.remove('show');
    setButtonLoading(btn, true);

    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();

        if (res.ok) {
            window.location.href = '/';
        } else {
            showError(errorDiv, data.error || 'Login failed');
            setButtonLoading(btn, false);
        }
    } catch (err) {
        showError(errorDiv, 'Network error. Please try again.');
        setButtonLoading(btn, false);
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const form = e.target;
    const btn = form.querySelector('button[type="submit"]');
    const errorDiv = document.getElementById('errorMessage');
    const username = form.username.value.trim();
    const password = form.password.value;
    const confirmPassword = form.confirmPassword.value;

    errorDiv.classList.remove('show');

    if (password !== confirmPassword) {
        showError(errorDiv, 'Passwords do not match');
        return;
    }

    setButtonLoading(btn, true);

    try {
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();

        if (res.ok) {
            window.location.href = '/login';
        } else {
            showError(errorDiv, data.error || 'Registration failed');
            setButtonLoading(btn, false);
        }
    } catch (err) {
        showError(errorDiv, 'Network error. Please try again.');
        setButtonLoading(btn, false);
    }
}
