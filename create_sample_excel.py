"""Generate a sample Excel file for testing the import feature."""
import pandas as pd

data = {
    'Name':       ['Aryan Sharma',   'Priya Mehta',   'Rohan Gupta',    'Sneha Iyer',    'Vikram Nair'],
    'Email':      ['aryan.sharma@example.com', 'priya.mehta@example.com',
                   'rohan.gupta@example.com',  'sneha.iyer@example.com',
                   'vikram.nair@example.com'],
    'Phone':      ['+91-9876543210', '+91-9123456789', '+91-9988776655',
                   '+91-8877665544', '+91-7766554433'],
    'Department': ['Engineering',   'Design',         'Marketing',      'HR',            'Finance'],
}

df = pd.DataFrame(data)
df.to_excel('sample_data.xlsx', index=False)
print("✅ sample_data.xlsx created with 5 sample users.")
