import lightgbm as lgb
import matplotlib.pyplot as plt

print("📊 Generating Feature Importance Chart (Task 31)...")

model = lgb.Booster(model_file='model_15m.txt')

ax = lgb.plot_importance(
    model, 
    importance_type='gain', 
    max_num_features=10, 
    figsize=(10, 6), 
    title='AI Transparency: What drives traffic predictions? (15m Forecast)',
    xlabel='Impact on Prediction Accuracy (Gain)',
    ylabel='Features (Inputs)'
)

plt.tight_layout()
plt.savefig('feature_importance.png', dpi=300)

print("✅ Done! The chart has been saved as 'feature_importance.png'.")
print("👉 Give this image to Tamer for his presentation.")