$apiKey = $env:ANTHROPIC_API_KEY
if (-not $apiKey) {
    Write-Host "ERRO: Defina a variavel de ambiente ANTHROPIC_API_KEY antes de rodar este script."
    exit 1
}

$body = @{
    model = "claude-3-haiku-20240307"
    max_tokens = 64
    messages = @(
        @{
            role = "user"
            content = "Say: Connection established!"
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
        -Body $body -Encoding UTF8
    Write-Host "STATUS: OK"
    Write-Host "MODELO: $($response.model)"
    Write-Host "RESPOSTA: $($response.content[0].text)"
    Write-Host "TOKENS: input=$($response.usage.input_tokens) output=$($response.usage.output_tokens)"
} catch {
    $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
    $reader.BaseStream.Position = 0
    $reader.DiscardBufferedData()
    $responseBody = $reader.ReadToEnd()
    Write-Host "ERRO HTTP: $($_.Exception.Response.StatusCode)"
    Write-Host "DETALHE: $responseBody"
}
