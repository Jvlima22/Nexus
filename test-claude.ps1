$apiKey = $env:ANTHROPIC_API_KEY
if (-not $apiKey) {
    Write-Host "❌ Defina a variavel de ambiente ANTHROPIC_API_KEY antes de rodar este script."
    exit 1
}

$body = @{
    model = "claude-3-haiku-20240307"
    max_tokens = 64
    messages = @(
        @{
            role = "user"
            content = "Responda apenas: Conexao com Nexus Trader estabelecida com sucesso!"
        }
    )
} | ConvertTo-Json -Depth 5

$headers = @{
    "x-api-key"         = $apiKey
    "anthropic-version" = "2023-06-01"
    "content-type"      = "application/json"
}

try {
    $response = Invoke-RestMethod -Uri "https://api.anthropic.com/v1/messages" `
        -Method POST `
        -Headers $headers `
        -Body $body
    Write-Host "✅ STATUS: OK"
    Write-Host "🤖 MODELO: $($response.model)"
    Write-Host "💬 RESPOSTA: $($response.content[0].text)"
    Write-Host "📊 TOKENS USADOS: input=$($response.usage.input_tokens) output=$($response.usage.output_tokens)"
} catch {
    Write-Host "❌ ERRO: $_"
}
