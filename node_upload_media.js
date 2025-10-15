#!/usr/bin/env node
// Minimal helper to upload a file to Notion using fileUploads API (Node SDK v4)
// Usage: node node_upload_media.js <NOTION_PAGE_URL_OR_ID> <FILE_PATH>

const { Client } = require('@notionhq/client');
const fs = require('fs');
const path = require('path');
const { Blob } = require('buffer');

function extractPageId(input) {
  if (!input) return '';
  // accept either URL or hyphenated/compact id
  const m = (input || '').match(/([a-f0-9]{32}|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/i);
  if (!m) return input;
  const raw = m[1].replace(/-/g, '');
  return `${raw.slice(0, 8)}-${raw.slice(8, 12)}-${raw.slice(12, 16)}-${raw.slice(16, 20)}-${raw.slice(20)}`;
}

async function main() {
  const [,, pageArg, filePath] = process.argv;
  if (!pageArg || !filePath) {
    console.error('[node_upload_media] usage: node node_upload_media.js <pageUrlOrId> <filePath>');
    process.exit(2);
  }
  const token = process.env.NOTION_API_KEY || process.env.NOTION_TOKEN;
  if (!token) {
    console.error('[node_upload_media] NOTION_API_KEY (or NOTION_TOKEN) is not set');
    process.exit(3);
  }

  const notion = new Client({ auth: token });

  const pageId = extractPageId(pageArg);
  const stat = fs.statSync(filePath);
  const fileName = path.basename(filePath);
  const isImage = /\.(png|jpg|jpeg|gif|webp|svg)$/i.test(fileName);
  const mime = isImage ? (fileName.toLowerCase().endsWith('.png') ? 'image/png'
    : fileName.toLowerCase().endsWith('.jpg') || fileName.toLowerCase().endsWith('.jpeg') ? 'image/jpeg'
    : fileName.toLowerCase().endsWith('.gif') ? 'image/gif'
    : fileName.toLowerCase().endsWith('.webp') ? 'image/webp'
    : fileName.toLowerCase().endsWith('.svg') ? 'image/svg+xml'
    : 'application/octet-stream')
    : 'application/octet-stream';
  const chunkSize = 10 * 1024 * 1024; // 10MB

  try {
    let fileUploadId = '';
    if (stat.size < 20 * 1024 * 1024) {
      // single part
      const created = await notion.fileUploads.create({ mode: 'single_part' });
      const data = fs.readFileSync(filePath);
      const sent = await notion.fileUploads.send({
        file_upload_id: created.id,
        file: {
          filename: fileName,
          data: new Blob([data], { type: mime }),
        },
      });
      fileUploadId = sent.id;
    } else {
      // multi part
      const parts = Math.ceil(stat.size / chunkSize);
      const created = await notion.fileUploads.create({ mode: 'multi_part', number_of_parts: parts, filename: fileName });
      const fd = fs.openSync(filePath, 'r');
      const buf = Buffer.alloc(chunkSize);
      for (let i = 1; i <= parts; i++) {
        const start = (i - 1) * chunkSize;
        const remaining = Math.min(chunkSize, stat.size - start);
        const { bytesRead } = fs.readSync(fd, buf, 0, remaining, start);
        const chunk = buf.subarray(0, bytesRead);
        await notion.fileUploads.send({
          file_upload_id: created.id,
          part_number: String(i),
          file: {
            filename: fileName,
            data: new Blob([chunk], { type: mime }),
          },
        });
      }
      fs.closeSync(fd);
      const completed = await notion.fileUploads.complete({ file_upload_id: created.id });
      fileUploadId = completed.id;
    }

    await notion.blocks.children.append({
      block_id: pageId,
      children: [
        isImage ? {
          type: 'image',
          image: { type: 'file_upload', file_upload: { id: fileUploadId } },
        } : {
          type: 'file',
          file: { type: 'file_upload', file_upload: { id: fileUploadId } },
        },
      ],
    });

    process.stdout.write(`[node_upload_media] ok page=${pageId} file=${fileName}\n`);
  } catch (e) {
    process.stderr.write(`[node_upload_media] error ${String(e)}\n`);
    process.exit(1);
  }
}

main();


