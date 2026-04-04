from locust import HttpUser, task, between

class URLShortenerUser(HttpUser):
    wait_time = between(0.5, 1)
    short_codes = []

    def on_start(self):
        # Create a URL to redirect to during the test
        res = self.client.post("/shorten", json={"url": "https://example.com"})
        if res.status_code == 201:
            self.short_codes.append(res.json()["short_code"])

    @task(1)
    def shorten_url(self):
        res = self.client.post("/shorten", json={"url": "https://example.com"})
        if res.status_code == 201:
            self.short_codes.append(res.json()["short_code"])

    @task(5)
    def redirect_url(self):
        # Hit cached redirects - this is where Redis shines
        if self.short_codes:
            code = self.short_codes[0]  # hit same URL repeatedly = cache hits
            self.client.get(f"/{code}", allow_redirects=False)

    @task(1)
    def health_check(self):
        self.client.get("/health")