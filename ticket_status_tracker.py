"""
Project Ticket Status Tracker
------------------------------
This script compares the status of project tickets across two reporting periods,
identifies changes (new, dropped, delayed tickets), and prepares a clean dataset
for Sankey diagram visualisation in Power BI or similar tools.

The script demonstrates:
- Data processing and transformation with pandas
- Status normalisation and mapping
- Period-over-period comparison
- Export of structured data for visualisation
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# === 1. Generate mock data ===
np.random.seed(42)

statuses = ['Open', 'In review', 'Resolved', 'Closed', 'Escalated', 'On hold']
timeliness_options = ['On track', 'Owner delay', 'Team delay', 'N/A']
priorities = ['High', 'Medium', 'Low']

def generate_mock_tickets(n, id_start=1):
    return pd.DataFrame({
        'id': [f'TKT{str(i).zfill(4)}' for i in range(id_start, id_start + n)],
        'status': np.random.choice(statuses, n),
        'timeliness': np.random.choice(timeliness_options, n),
        'priority': np.random.choice(priorities, n, p=[0.3, 0.5, 0.2])
    })

# Simulate two reporting periods with partial overlap
df_q1 = generate_mock_tickets(80, id_start=1)
df_q2 = generate_mock_tickets(85, id_start=10)  # Overlapping IDs to simulate continuity

# === 2. Identify new and dropped tickets ===
id_q1 = set(df_q1['id'])
id_q2 = set(df_q2['id'])
dropped_ids = id_q1 - id_q2
new_ids = id_q2 - id_q1

df_q1.loc[df_q1['id'].isin(dropped_ids), 'status'] = 'Dropped'
df_q2.loc[df_q2['id'].isin(new_ids), 'status'] = 'New'

# === 3. Keep relevant columns ===
df_q1 = df_q1[['id', 'status', 'timeliness']].copy()
df_q2 = df_q2[['id', 'status', 'timeliness', 'priority']].copy()

# === 4. Normalise status labels ===
def normalize_status(status):
    if pd.isna(status):
        return ''
    status = status.strip()
    mapping = {
        'Resolved': 'Completed',
        'Closed': 'Completed',
        'Escalated': 'Pending escalation',
        'On hold': 'Pending follow-up',
        'In review': 'In progress',
        'Open': 'In progress'
    }
    return mapping.get(status, status)

df_q1['status'] = df_q1['status'].apply(normalize_status)
df_q2['status'] = df_q2['status'].apply(normalize_status)

# === 5. Rename columns for merge ===
df_q1 = df_q1.rename(columns={'status': 'status_q1', 'timeliness': 'timeliness_q1'})
df_q2 = df_q2.rename(columns={'status': 'status_q2', 'timeliness': 'timeliness_q2'})

# === 6. Merge across periods ===
df = pd.merge(df_q1, df_q2, on='id', how='outer')

# === 7. Tag delays ===
delay_keywords = ['Owner delay', 'Team delay']
delay_eligible = ['In progress', 'Pending follow-up', 'Pending escalation']

def tag_delay(status, timeliness):
    if pd.isna(status):
        return ''
    if status in delay_eligible and timeliness in delay_keywords:
        return f"{status}|delayed"
    return status

df['status_q1'] = df.apply(lambda r: tag_delay(r['status_q1'], r['timeliness_q1']), axis=1)
df['status_q2'] = df.apply(lambda r: tag_delay(r['status_q2'], r['timeliness_q2']), axis=1)

# === 8. Filter out irrelevant transitions ===
df_filtered = df[
    (df['status_q1'] != 'Dropped') &
    (df['status_q2'] != 'New') &
    df['status_q1'].notna() &
    df['status_q2'].notna() &
    ~((df['status_q1'].str.startswith('Completed')) & (df['status_q2'].str.startswith('Completed')))
]

# === 9. Summary statistics ===
print("=== Status Distribution Q1 ===")
print(df['status_q1'].value_counts())
print("\n=== Status Distribution Q2 ===")
print(df['status_q2'].value_counts())
print(f"\n=== Tickets with delays in Q2: {df_filtered['status_q2'].str.contains('delayed').sum()} ===")

# === 10. Visualisation: Status transition heatmap ===
transition_matrix = pd.crosstab(
    df_filtered['status_q1'].str.replace('|delayed', ' (delayed)', regex=False),
    df_filtered['status_q2'].str.replace('|delayed', ' (delayed)', regex=False)
)

fig, ax = plt.subplots(figsize=(10, 6))
im = ax.imshow(transition_matrix.values, cmap='YlOrRd', aspect='auto')
plt.colorbar(im, ax=ax, label='Number of tickets')
ax.set_xticks(range(len(transition_matrix.columns)))
ax.set_yticks(range(len(transition_matrix.index)))
ax.set_xticklabels(transition_matrix.columns, rotation=45, ha='right', fontsize=9)
ax.set_yticklabels(transition_matrix.index, fontsize=9)
ax.set_xlabel('Status Q2', fontsize=11)
ax.set_ylabel('Status Q1', fontsize=11)
ax.set_title('Ticket Status Transitions: Q1 → Q2', fontsize=13, fontweight='bold')

for i in range(len(transition_matrix.index)):
    for j in range(len(transition_matrix.columns)):
        val = transition_matrix.values[i, j]
        if val > 0:
            ax.text(j, i, str(val), ha='center', va='center', fontsize=9,
                   color='black' if val < transition_matrix.values.max() * 0.7 else 'white')

plt.tight_layout()
plt.savefig('ticket_transitions_heatmap.png', dpi=150, bbox_inches='tight')
plt.show()
print("\n✅ Heatmap saved as ticket_transitions_heatmap.png")

# === 11. Export for Sankey visualisation in Power BI ===
output_path = "sankey_ready_for_powerbi.csv"
df_filtered[['id', 'status_q1', 'status_q2', 'priority']].to_csv(output_path, index=False)
print(f"✅ Sankey-ready file exported to {output_path}")
