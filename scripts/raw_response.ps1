$body = @{ model = "qwen3:1.7b"; prompt = "Say hello in JSON"; stream = $false } | ConvertTo-Json
(Invoke-WebRequest -UseBasicParsing -Uri http://localhost:11434/api/generate -Method Post -ContentType "application/json" -Body $body).Content
