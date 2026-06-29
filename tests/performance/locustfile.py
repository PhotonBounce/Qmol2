from locust import HttpUser, task, between

class QMolUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Optional: sign up for a free API key before load test."""
        # Uncomment if you want to generate a key per user:
        # r = self.client.post("/v1/signup", json={"email": f"loadtest_{self.user_id}@example.com"})
        # if r.status_code == 200:
        #     self.api_key = r.json()["api_key"]
        # else:
        #     self.api_key = None
        self.api_key = None
    
    @task(5)
    def compute_single(self):
        self.client.post("/v1/compute", json={"smiles": ["CCO"]})
    
    @task(3)
    def compute_batch(self):
        self.client.post("/v1/compute", json={"smiles": ["CCO", "c1ccccc1", "CC(C)C"]})
    
    @task(2)
    def predict(self):
        if self.api_key:
            self.client.post(
                "/v1/predict",
                json={"smiles": ["CCO"]},
                headers={"x-api-key": self.api_key}
            )
        else:
            self.client.post("/v1/compute", json={"smiles": ["CCO"]})
    
    @task(1)
    def descriptors(self):
        if self.api_key:
            self.client.post(
                "/v1/descriptors",
                json={"smiles": ["CCO"]},
                headers={"x-api-key": self.api_key}
            )
        else:
            self.client.post("/v1/compute", json={"smiles": ["CCO"]})
    
    @task(1)
    def health_check(self):
        self.client.get("/v1/health")
    
    @task(1)
    def ready_check(self):
        self.client.get("/v1/ready")
