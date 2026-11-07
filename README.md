This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

On a fresh install, these are the following steps to running the MediRounds app locally:

### 1. **Create necessary environment files.**
- There are three .env.example files: one in the parent MEDIRounds directory, one in frontend, and one in backend
- We need to copy the .env.example files over into real .env files that the docker containers. Create three .env files in these directories, and copy the .env.example content from each of those directories into those files
- Set each instance of BETTER_AUTH_SECRET in the .env files to the same, randomly generated value. The following command can be used to generate this value:
```bash
openssl rand -base64 32
```
### 2. **Run the application through docker**
- The docker compose YAML manifest is configured to run all necessary parts of the application with a single command.
```bash
docker compose up -d
```
- On first run, this will automatically propogate the database with the necessary tables. If you've previously ran the application with an out of date database version, you may have to rebuild your images and volumes. If you run into errors, try the following:
```bash
docker compose down -v
docker compose up --build
```
### 3. **IF RUNNING THROUGH DOCKER DOESN'T WORK**
- On computers with memory restrictions, it is possible running the docker composes will create a WSL out of memory error
- If you encounter this error, instead of running all application components through docker we can run some on our computer to free up WSL memory. It is recommended to also create a python virtual environment to keep libraries for this app isolated.
- Clear any previous medirounds containers and volumes with
```bash
docker compose down -v
``` 
- Afterwords, run only the pgadmin, postgres, and mailpit containers with 
```bash
docker compose up -d postgres pgadmin mailpit
```
- from the backend directory, install the required python libraries, override the powershell session's environment to run with localhost (instead of a docker container), and start the application. 
```bash
pip install -r requirements.txt
$env:DATABASE_URL = "postgresql+asyncpg://medirounds_app:pasword123@localhost:5432/medirounds_db"
uvicorn app.main:app --reload --port 8000
```
- from the frontend directory, with nodejs installed, run the frontend:
```bash
npm install
npm run dev
```

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
