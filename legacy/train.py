import torch
import torch.nn as nn
import numpy as np
from sklearn.preprocessing import StandardScaler
from torch.utils.data import Dataset, DataLoader

sc = StandardScaler()

class CustomDataset(Dataset):
    def __init__(self):
        xy = np.loadtxt("Data.csv", delimiter=",", dtype=np.float32, skiprows=1)
        self.x = torch.from_numpy(sc.fit_transform(xy[:72, 2:]))
        self.y = torch.from_numpy(xy[:72, [1]].astype(np.float32))  # Cast labels to float
        self.n_samples = 72
        self.n_features = xy.shape[1] - 2

    def __getitem__(self, index):
        return self.x[index], self.y[index]

    def __len__(self):
        return self.n_samples

class LogisticRegression(nn.Module):
    def __init__(self, input_size):
        super(LogisticRegression, self).__init__()
        self.linear = nn.Linear(input_size, 1)

    def forward(self, x):
        y_pred = torch.sigmoid(self.linear(x))
        return y_pred
dataset = CustomDataset()
dataloader = DataLoader(dataset=dataset, batch_size=4, shuffle=True, num_workers=0)

# Model and training setup
model = LogisticRegression(dataset.n_features)
criterion = nn.BCELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    
def training():
    
    # Training loop
    num_epochs = 100
    for epoch in range(num_epochs):
        for inputs, labels in dataloader:
            # Forward pass
            y_pred = model(inputs)
            loss = criterion(y_pred, labels)
            # Backward pass and optimization
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
    return model
    # Predict
    
def transform(input):
    x = sc.transform(input)
    return x
# Example input


if __name__ == '__main__':
    y_pred = training(input)
    confidence = y_pred.item() * 100
    if y_pred >= 0.5:
        print(1)
        print(f"Confidence: {confidence:.2f}%")
    else:
        print(0)
        print(f"Confidence: {(100 - confidence):.2f}%")

        