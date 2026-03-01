import { chromium } from 'playwright';
import fs from 'fs';

async function run() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  await page.goto('https://www.asambleamadrid.es/actividad-parlamentaria/publicaciones/diarios-de-sesiones');
  console.log('Loaded page. Title:', await page.title());
  
  // Let's just grab all PDF links as a test
  const links = await page.$$eval('a[href$=".pdf"]', els => els.map(e => e.href));
  console.log('Found PDF links:', links.length);
  
  await browser.close();
}

run();
