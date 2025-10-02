const api = {
    login: async (username, password) => {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',  // ✅ MUST HAVE THIS
            body: JSON.stringify({ username, password })
        });
        return await response.json();
    },
    
    // For ALL other API calls, also add:
    credentials: 'include'
}
