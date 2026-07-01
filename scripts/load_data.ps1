Write-Host "Loading users data..."
python manage.py loaddata data/users_data.json

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to load users_data.json"
    exit $LASTEXITCODE
}

Write-Host "Loading spacenter data..."
python manage.py loaddata data/spacenter.json

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to load spacenter.json"
    exit $LASTEXITCODE
}

Write-Host "All data loaded successfully."
