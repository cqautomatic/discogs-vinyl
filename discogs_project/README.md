# 🎵 Discogs Collection Management Project

## Docker Quick Start

The fastest way to run the full stack on any machine:

```bash
git clone <this-repo>
cd discogs_project
make setup        # copies .env templates — fill in POSTGRES_PASSWORD + DISCOGS_TOKEN
make up           # builds images, starts postgres + api + react
make migrate      # runs DB migrations (first time only)
```

Open **http://localhost** — the React UI is served via nginx, API calls proxy automatically.

| Command | Description |
|---|---|
| `make up` | Start all services |
| `make down` | Stop all services |
| `make migrate` | Run DB migrations |
| `make logs` | Tail all service logs |
| `make clean` | Stop + wipe all data volumes |

> **Prerequisites**: Docker Desktop (or Docker Engine + Compose plugin). That's it.

---

Transform your Discogs music collection into a powerful analytics platform using either PostgreSQL or Snowflake as the backend.

## 🚀 Quick Start Options

### Option 1: PostgreSQL + Streamlit (2-4 hours)
**Best for**: Learning SQL, local development, full control
- ✅ **Setup Time**: 30 mins
- 🎯 **Completion Time**: 2-4 hours 
- 📊 **What You'll Build**: Full-featured collection browser with analytics
- 📍 **Guide**: [PostgreSQL App README](./apps/postgres/discogs_collection_postgres_lab/README.md)

### Option 2: Snowflake SiS (1-2 hours)  
**Best for**: Cloud analytics, modern data stack, scalability
- ✅ **Setup Time**: 15 mins
- 🎯 **Completion Time**: 1-2 hours
- 📊 **What You'll Build**: Cloud-native collection analyzer  
- 📍 **Guide**: [Snowflake App README](./apps/snowflake/discogs_collection_snowflake/README.md)

## 🎯 What You'll Learn

### Core Skills
- **API Integration**: Real-time data ingestion from Discogs API
- **Data Modeling**: Music collection schema design
- **Analytics**: Genre trends, decade analysis, collection insights
- **UI Development**: Interactive Streamlit dashboards

### Database Skills
- **PostgreSQL**: JSONB, full-text search, advanced indexing
- **Snowflake**: VARIANT data types, Snowpark, SiS development

### Advanced Features
- 🖼️ **Artwork Management**: Download and display album covers
- 🔍 **Smart Search**: Full-text and semantic search capabilities  
- 📈 **ML Insights**: Collection completeness scoring and recommendations
- 🎨 **Interactive Visualizations**: Clickable charts with drill-down analytics

## 📁 Project Structure
```
discogs_project/
├── apps/
│   ├── postgres/              # PostgreSQL + Streamlit app (2-4 hrs)
│   └── snowflake/             # Snowflake SiS app (1-2 hrs)
├── scripts/                   # Shared utilities
└── tests/                     # Comprehensive test suite (62 tests)
```

## ⚡ Prerequisites

### Required
- **Discogs Account**: Free account at [discogs.com](https://discogs.com)
- **Python 3.8+**: For running scripts and apps
- **API Token**: Generate from Discogs Developer settings

### Database Options
- **PostgreSQL**: For local PostgreSQL app (Docker or native install)
- **Snowflake**: Free 30-day trial for cloud app

## 🧪 Verification
```bash
# Run comprehensive test suite (62 tests)
python -m pytest discogs_project/tests -v

# Test specific components
python -m pytest discogs_project/tests/postgres_app -v    # PostgreSQL app tests
python -m pytest discogs_project/tests/snowflake_app -v   # Snowflake app tests
```

## 🏆 Success Criteria

After completing either path, you'll have:
- ✅ **Working Collection Browser**: Interactive web interface
- ✅ **Analytics Dashboard**: Genre, decade, and artist insights  
- ✅ **Search Capabilities**: Find releases across your collection
- ✅ **Data Pipeline**: Automated collection synchronization
- ✅ **Artwork Gallery**: Visual browsing with full-size images

## 🆘 Getting Help

1. **Setup Issues**: Check app-specific README troubleshooting sections
2. **API Problems**: Verify Discogs token and rate limits  
3. **Database Issues**: Review connection settings and permissions
4. **Performance**: Monitor query execution and optimize indexes

Choose your path and start building! 🎵
