# Interview Task for Backend Developer

## General Requirements

- **File Integrity**: 
    - Do not modify any files within the `internal` directory.
    - Do not modify the provided Dockerfile-store file
    - You can modify the port mappings if needed, in the docker-compose.yml
    - Do not interact directly with any file in the `internal` directory. You should use docker compose to run the `ebay` and `amazon` store containers and interact with them only via network.
- **Documentation**: Include a `README.md` file with instructions on how to run and test your solution.
- **AI Tools**: Usage of Generative AI tools, such as ChatGPT, is strictly prohibited. Detection of such tools will result in immediate disqualification.
- **Design Freedom**: You have the freedom to design the classes, data models, and their responsibilities. The end result must provide a clear and documented API definition that meets the requirements.
- **Code Quality**: High-quality, maintainable code is crucial.
- **Error Handling**:  First, make sure the happy flow works well. Handling errors or unexpected situations is a nice bonus.
- **Submission**: Submit your solution and the original source files using a private github repository with the user `ilyahzoomd` as a collaborator. Your code should be contained within a Python package named `solution`.
- **Need Help?**: If some part of the description is unclear or any advice is needed, feel free to contact me via Whatsapp or Email.
```
.
├── internal/
│   ├── ...                   : internal files - SHOULD NOT BE CHANGED ...
├── solution/
│   ├── ...                   : Your solution files here ...
├── docker-compose.yml        : The provided docker_compose.yml
├── Dockerfile-store          : The provided Dockerfile-store - SHOULD NOT BE CHANGED 
├── ...                       : your Dockerfile should be added here if needed ...
└── README.md                 : Your documentation here
```

## Task Description

### Overview

Develop a backend for an online stores price comparison platform. (Like [zap.co.il](https://www.zap.co.il/))

In this exercise, the platform should interact with the simulations of Amazon and Ebay via Rest API. Each store is represented by a service in the given `docker-compose.yml` and provides a single API endpoint for retrieving products. The system's core functionalities will include registering online stores (in this case only Ebay and Amazon), adding products, linking products to specific stores, and fetching pricing data through API interactions.

### Provided Store (Ebay or Amazon Simulations) API Details

- **Endpoint**: `GET products`
- **Filter**: A name filter can be provided in the query, e.g., `?name_contains="Laptop"`. This returns products with names containing "Laptop".
- **Response**: If no products match the filter, the endpoint returns an empty list.

## Backend Requirements

### Non-Functional Requirements

- **Framework**: Utilize your preferred Python web framework (Django, Flask, FastAPI, etc.).
- **Database**: Integrate with a MySQL database hosted in the `mysql_db` container from your `docker-compose.yml`. Pay attention to port mappings and change them if required.
- **ORM**: Implement database interactions using an ORM.
- **Testing**: Each endpoint must have at least one unit test. Integration tests are optional.
- **Environment Variables**: If your solution needs any environment variables, such as those defined in a `.env` file, include a `.env.sample` file or detail the necessary setup in your README.md.
- **Documentation**: Provide endpoint documentation and usage examples.

### Functional Requirements

Your application should provide the following endpoints:

1. **POST Register Store**: Register a new online store.
2. **POST Register Product**: Register a new product and associate it with a store.
3. **GET Search**:
   - **Input**: Part of a product name provided via the query string.
   - **Behavior**: Searches for products registered in our system where the name contains the provided name part. If no products are found, returns an empty list. If found, it returns them with their up-to-date pricing from the respective stores.
   - **Output**: A sorted list of products by price in ascending order. Each product may appear multiple times if it's offered by different stores.
   - **Details**: Each product entry in the list will include:
     - Full product name
     - Store name
     - Current price

### Bonus Points

- **Performance**: Ensure every call to the Search endpoint, except maybe the first one,  returns results in less than two seconds, given the information that the online store prices update only once daily.
- **Containerization**: Dockerize your backend service and integrate it into the provided `docker_compose.yml`.
