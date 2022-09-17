use std::time::{SystemTime, UNIX_EPOCH};

use sqlx::{sqlite::SqlitePoolOptions, Pool, Sqlite};
use uuid::Uuid;

static CONNECTION_STRING: &str = "sqlite://data/database.sqlite";

pub struct Database(Pool<Sqlite>);

impl Database {
    pub async fn new() -> anyhow::Result<Self> {
        let pool = SqlitePoolOptions::new()
            .max_connections(5)
            .connect(CONNECTION_STRING)
            .await?;

        sqlx::migrate!("./migrations").run(&pool).await?;

        Ok(Self(pool))
    }

    pub async fn add(&self, id: Uuid, data: &[u8]) -> anyhow::Result<()> {
        let date = unix_epoc()?;
        sqlx::query!(
            "insert into images (id, data, date) values ($1, $2, $3)",
            id,
            data,
            date
        )
        .execute(&self.0)
        .await?;

        Ok(())
    }

    pub async fn get(&self, id: Uuid) -> anyhow::Result<Option<Image>> {
        sqlx::query_as!(
            Image,
            r#"select
                    id "id: Uuid",
                    data,
                    date
                from images where id = $1"#,
            id
        )
        .fetch_optional(&self.0)
        .await
        .map_err(anyhow::Error::from)
    }

    pub async fn delete(&self, id: Uuid) -> anyhow::Result<bool> {
        let result = sqlx::query!("delete from images where id = $1", id)
            .execute(&self.0)
            .await?;
        Ok(result.rows_affected() > 0)
    }

    pub async fn clear(&self) -> anyhow::Result<(i32, i32)> {
        let summary = sqlx::query!(
            r#"select count(*) num_items, ifnull(sum(length(data)), 0) as total_size from images"#
        )
        .fetch_one(&self.0)
        .await?;

        let _ = sqlx::query!("delete from images").execute(&self.0).await?;

        Ok((summary.num_items, summary.total_size.unwrap_or_default()))
    }
}

pub struct Image {
    pub id: Uuid,
    pub data: Vec<u8>,
    pub date: i64,
}

fn unix_epoc() -> anyhow::Result<u32> {
    Ok(SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs() as u32)
}
