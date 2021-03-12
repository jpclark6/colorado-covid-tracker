# Colorado COVID Data

### Colorado COVID data updated daily, including vaccine stats, daily infections, hospitalizations, and deaths due to COVID.


<br>
<details open="open">
  <summary><h2 style="display: inline-block">Table of Contents</h2></summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#how-it-works">How it works</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

[<img src="./images/dashboard.png" height="500px"/>](https://coloradocoviddata.com)

When I was looking around the web for Colorado COVID data the [Colorado government website](https://covid19.colorado.gov/data) had some good data and charts, but they were in a cluttered website with lots of data I wasn't interested in. This project delivers a simple layout of the data I wanted to see and updates the data daily automatically as soon as it's available. 

This repo is for the API and for fetching data. The front end repo can be found [here](https://github.com/jpclark6/colorado-covid-frontend)


### Built With

* [AWS SAM](https://aws.amazon.com/serverless/sam/)
* [AWS Lambda](https://aws.amazon.com/lambda/)
* [Python](https://www.python.org/)



## Getting Started

To get a copy up and running follow these simple steps.

### Prerequisites

This project assumes you have an empty Postgres database handy. You will also need the AWS SAM CLI installed, and an AWS account.

You will also need to have some parameters saved to AWS SSM Parameter Store. Specifically:

* Database credentials `/colorado-covid/database`
* Key to invalidate the cache `/colorado-covid/invalidate_cache_key`
* URL of this project, used to invalidate the cache `/colorado-covid/api_url`

### Installation

1. Clone the repo to your favorite directory.
    ```sh
    $ git clone https://github.com/jpclark6/colorado-covid-tracker.git
    $ cd colorado-covid-tracker
    ```

1. To run the migrations run the following script.
    ```sh
    $ ./scripts/setup.sh
    ```

1. Next optionally grab the currently hospitalized data file (since this data is strangely missing from the API) by following the directions after running the migration

1. Build and deploy the package
    ```sh
    $ sam build
    $ sam deploy --guided
    ```

1. The data will backfill automatically after it runs for the first time

### Running tests locally

1. Install the requirements
    ```sh
    $ pip install -r tests/requirements.txt -r src/etl/requirements.txt -r src/api/requirements.txt
    ```

2. Run the tests
    ```sh
    pytest
    ```


## How it works

When you deploy the package it creates the required resources to run this project. It creates five lambda functions. Two go out and grab vaccine and case from the CO government's APIs. One is the API function. One checks that data was successfully entered at the end of each day, and one is a health check to make sure the API is working properly. If anything fails along the way there is also an SNS topic that will email you about the issue.

Each function that grabs the API data first saves it to S3 in its raw form, then cleans the data and saves it to S3, and then loads the data into the Postgres DB for the API to use. The data comes in at a different time each day so the functions check every 10 minutes for new data throughout the evening from 4PM to 8PM. At 9PM the data-check lambda function confirms the day's data is in the database. As soon as new data is loaded the cached lambda data is invalidated and the new data becomes cached.

The API uses a lambda function with API Gateway. Since the data is valid until new data is available (once every 24 hours) the lambda function can cache the data and then invalidate it when needed. This allows nearly limitless capacity with even the smallest  databases since only one DB call is required. Data is automatically invalidated on a timeout, or when the endpoint to invalidate the data is hit with the correct API key.

## Roadmap

1. Get rid of psycopg2 and just use SQLAlchemy due to the increasing complexity of the tables
1. After new data comes out stop requesting data for the rest of the day
1. Find cool new data to save

## License

Distributed under the MIT License.


## Contact

[LinkedIn](https://linkedin.com/in/jpclark6)

