# Security

- Store API keys only in the hosting provider's secret/environment-variable store.
- Never commit real Bankr, market-data, email, wallet, or other credentials.
- Use least-privilege credentials where supported.
- Keep live deployment behind the risk governor and deployment policy.
- Treat logs as potentially sensitive and avoid printing credentials or authorization headers.
- Rotate credentials if they are accidentally exposed.
