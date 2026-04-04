from locust import HttpUser, task, between


class URLShortenerUser(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        """Create some URLs when user starts, store codes for later GETs."""
        self.short_codes = []
        for i in range(3):
            response = self.client.post("/shorten", json={
                "url": f"https://example.com/test/{i}"
            })
            if response.status_code == 201:
                data = response.json()
                self.short_codes.append(data["short_code"])

    @task(3)
    def shorten_url(self):
        """Create new short URLs."""
        self.client.post("/shorten", json={
            "url": "https://example.com/test"
        })

    @task(5)
    def get_url(self):
        """Fetch existing short URLs (tests Redis cache)."""
        if self.short_codes:
            code = self.short_codes[0]  # Reuse same code = cache hits
            self.client.get(f"/{code}", allow_redirects=False)

    @task(1)
    def health_check(self):
        self.client.get("/health")
