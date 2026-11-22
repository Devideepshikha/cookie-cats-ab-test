# Results

## Data checks

- 90,189 players, 0 duplicate user IDs, 0 missing values
- Removed 1 player(s) with more than 10,000 game rounds (max was 49,854)
- Players per group: 44,699 (gate_30) and 45,489 (gate_40); sample ratio check p = 0.009

## Retention

| Metric | gate_30 | gate_40 | Difference (pp) | z-test p-value | Bootstrap: chance gate_30 is better |
| --- | --- | --- | --- | --- | --- |
| retention_1 | 44.82% | 44.23% | 0.59 (95% CI -0.05 to 1.21) | 0.0739 | 96.5% |
| retention_7 | 19.02% | 18.20% | 0.82 (95% CI 0.33 to 1.32) | 0.0016 | 99.8% |

Game rounds played (Mann-Whitney U test): p = 0.051

## 7-day retention by engagement segment

| Rounds played | gate_30 | gate_40 |
| --- | --- | --- |
| 0 rounds | 0.8% | 0.6% |
| 1-10 | 1.9% | 1.9% |
| 11-30 | 8.6% | 7.8% |
| 31-100 | 28.4% | 26.2% |
| 100+ | 71.4% | 71.2% |
