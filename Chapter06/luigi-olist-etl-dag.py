# luigi_olist_etl_dag.py
import luigi
from etl_functions import extract, transform, load_to_database
import os
import datetime

class ExtractTask(luigi.Task):
    """
    Task to extract data from Kaggle.

    Returns:
        str: The path to the folder where the data has been extracted.
    """
    date = luigi.DateParameter(default=datetime.date.today())

    def output(self):
        return luigi.LocalTarget(f'./data/raw/{self.date}/')

    def complete(self):
        return self.output().exists() and len(os.listdir(self.output().path)) > 0

    def run(self):
        print(f"Starting ExtractTask for date: {self.date}")
        os.makedirs(self.output().path, exist_ok=True)
        extract(self.output().path)
        print("ExtractTask completed")

class TransformTask(luigi.Task):
    """
    Task to transform the extracted data.

    Returns:
        str: The path to the directory containing the processed data.
    """
    date = luigi.DateParameter(default=datetime.date.today())

    def requires(self):
        return ExtractTask(date=self.date)

    def output(self):
        return luigi.LocalTarget(f'./data/processed/{self.date}/')

    def complete(self):
        return self.output().exists() and len(os.listdir(self.output().path)) > 0

    def run(self):
        print(f"Starting TransformTask for date: {self.date}")
        os.makedirs(self.output().path, exist_ok=True)
        transform(self.input().path, self.output().path)
        print("TransformTask completed")

class LoadTask(luigi.Task):
    """
    Task to load the transformed data into a SQLite database.
    """
    date = luigi.DateParameter(default=datetime.date.today())
    db_name = luigi.Parameter(default="olist.db")

    def requires(self):
        return TransformTask(date=self.date)

    def output(self):
        return luigi.LocalTarget(f'{self.db_name}_{self.date}')

    def complete(self):
        return self.output().exists()

    def run(self):
        print(f"Starting LoadTask for date: {self.date}")
        load_to_database(self.input().path, self.output().path)
        print("LoadTask completed")

if __name__ == '__main__':
    luigi.build([LoadTask()], local_scheduler=False)
