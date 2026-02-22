import matplotlib.pyplot as plt
import pandas as pd

# 1. Load the data (assuming you exported it to 'mulval_results.csv')
# If you haven't exported yet, you can use the results from your lists
df = pd.read_csv('mulval_rdn_results.csv')

# 2. Configure the plot
plt.figure(figsize=(10, 6))

# Plot Positive Scenarios
plt.plot(df['Tree'], df['Avg_Pos_Prob'], 
         label='Positive Scenarios (Full Exploit Path)', 
         color='#2ecc71', marker='o', linewidth=2)

# Plot Negative Scenarios
plt.plot(df['Tree'], df['Avg_Neg_Prob'], 
         label='Negative Scenarios (Broken Chain)', 
         color='#e74c3c', marker='x', linewidth=2)

# 3. Add Labels and Titles (In English for your slides)
plt.title('SRLearn Probability Convergence: MulVAL Logic Path', fontsize=14, pad=20)
plt.xlabel('Number of Boosting Trees (Iterations)', fontsize=12)
plt.ylabel('Attack Success Probability', fontsize=12)
plt.ylim(0, 1.05) # Keeps the probability scale consistent
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend(loc='best', fontsize=10)

# 4. Final touches
plt.tight_layout()
plt.savefig('mulval_logic_plot.png', dpi=300) # Save high quality for slides
plt.show()