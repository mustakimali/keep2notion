use actix_multipart::{Multipart, MultipartError};
use actix_web::{delete, get, post, web, App, HttpResponse, HttpServer, Responder};
use db::Database;
use serde_json::json;
use std::{io::Cursor, sync::Arc};
use thiserror::Error;
use tracing::Instrument;
use tracing_actix_web::TracingLogger;
use uuid::Uuid;

mod db;

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    use tracing_bunyan_formatter::{BunyanFormattingLayer, JsonStorageLayer};
    use tracing_subscriber::layer::SubscriberExt;
    use tracing_subscriber::{EnvFilter, Registry};

    let env_filter = EnvFilter::try_from_default_env().unwrap_or(EnvFilter::new("info"));
    let formatting_layer = BunyanFormattingLayer::new("image-server".to_string(), std::io::stdout);

    let subscriber = Registry::default()
        .with(env_filter)
        .with(JsonStorageLayer)
        .with(formatting_layer);

    tracing::subscriber::set_global_default(subscriber).unwrap();

    start()
        .instrument(tracing::info_span!("start application"))
        .await
}

async fn start() -> std::io::Result<()> {
    let port = std::env::var("PORT")
        .unwrap_or("8000".into())
        .parse()
        .unwrap_or(8000);

    let db = Database::new().await.expect("init database");
    let ctx = AppContext { db };
    let ctx = Arc::new(ctx);

    HttpServer::new(move || {
        App::new()
            .app_data(web::Data::new(ctx.clone()))
            .wrap(TracingLogger::default())
            .service(health)
            .service(image_stats)
            .service(image_get)
            .service(image_post)
            .service(image_delete)
            .service(image_clear)
    })
    .bind(("0.0.0.0", port))?
    .run()
    .await
}

struct AppContext {
    db: Database,
}

#[derive(Error, Debug)]
enum AppError {
    #[error("Invalid Image Format")]
    InvalidImageFormat,
    #[error("RequestError")]
    RequestError(#[from] MultipartError),
    #[error("Internal Server Error: {0}")]
    Unknown(#[from] anyhow::Error),
}

impl actix_web::ResponseError for AppError {
    fn status_code(&self) -> actix_web::http::StatusCode {
        use actix_web::http::StatusCode;
        match self {
            AppError::Unknown(_) => StatusCode::INTERNAL_SERVER_ERROR,
            AppError::RequestError(_) | AppError::InvalidImageFormat => StatusCode::BAD_REQUEST,
        }
    }

    fn error_response(&self) -> HttpResponse<actix_web::body::BoxBody> {
        let body = json!({
            "error": self.to_string()
        })
        .to_string();

        HttpResponse::new(self.status_code()).set_body(actix_web::body::BoxBody::new(body))
    }
}

#[get("/health")]
#[tracing::instrument]
async fn health() -> impl Responder {
    HttpResponse::Ok()
}

#[post("/{id}.{ext}")]
#[tracing::instrument(skip(state, payload))]
async fn image_post(
    state: web::Data<Arc<AppContext>>,
    param: web::Path<(Uuid, String)>,
    mut payload: Multipart,
) -> Result<impl Responder, AppError> {
    use futures_util::TryStreamExt;

    let id = param.0;
    let mut file_data = Vec::<u8>::new();
    while let Some(mut field) = payload.try_next().await? {
        let content_disposition = field.content_disposition();
        let field_name = content_disposition
            .get_name()
            .ok_or_else(|| anyhow::anyhow!("content disposition header not found"))?;

        match field_name {
            "file" => {
                while let Some(chunk) = field.try_next().await? {
                    file_data.extend_from_slice(&chunk);
                }
            }
            "layout" => {}
            _ => {}
        }
    }

    // validate
    let _ = image::io::Reader::new(Cursor::new(file_data.clone()))
        .with_guessed_format()
        .map_err(|_| AppError::InvalidImageFormat)?
        .decode()
        .map_err(|_| AppError::InvalidImageFormat)?;

    let id = id.clone();
    state.db.add(id.clone(), &file_data).await?;

    Ok(HttpResponse::Accepted().body(
        json!({
            "id": id,
            "size": file_data.len()
        })
        .to_string(),
    ))
}

#[get("/{id}.{ext}")]
#[tracing::instrument(skip(state))]
async fn image_get(
    state: web::Data<Arc<AppContext>>,
    param: web::Path<(Uuid, String)>,
) -> Result<impl Responder, AppError> {
    let id = param.0;
    let image = state.db.get(id.clone()).await?;

    let result = match image {
        Some(image) => HttpResponse::Ok()
            .append_header(("x-upload-date", image.date))
            .body(image.data),
        None => HttpResponse::NotFound().finish(),
    };

    Ok(result)
}

#[delete("/{id}.{ext}")]
#[tracing::instrument(skip(state))]
async fn image_delete(
    state: web::Data<Arc<AppContext>>,
    param: web::Path<(Uuid, String)>,
) -> Result<impl Responder, AppError> {
    let id = param.0;
    let success = state.db.delete(id.clone()).await?;

    Ok(if success {
        HttpResponse::Ok().finish()
    } else {
        HttpResponse::NotFound().finish()
    })
}

#[delete("/_all_")]
#[tracing::instrument(skip(state))]
async fn image_clear(state: web::Data<Arc<AppContext>>) -> Result<impl Responder, AppError> {
    if let Ok((num_items, total_size)) = state.db.clear().await {
        Ok(HttpResponse::Ok().body(
            json!({
                "total_items": num_items,
                "total_size_bytes": total_size
            })
            .to_string(),
        ))
    } else {
        Ok(HttpResponse::NotFound().finish())
    }
}

#[get("/_stats_")]
#[tracing::instrument(skip(state))]
async fn image_stats(state: web::Data<Arc<AppContext>>) -> Result<impl Responder, AppError> {
    if let Ok((num_items, total_size)) = state.db.stats().await {
        Ok(HttpResponse::Ok().body(
            json!({
                "total_items": num_items,
                "total_size_bytes": total_size
            })
            .to_string(),
        ))
    } else {
        Ok(HttpResponse::NotFound().finish())
    }
}
