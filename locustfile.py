from locust import HttpUser, task, between

class URLShortenerUser(HttpUser):
    wait_time = between(1, 2)

    @task(3)
    def shorten_url(self):
        self.client.post("/shorten", json={
            "url": "https://example.com/test"
        })

    @task(1)
    def health_check(self):
        self.client.get("/health")