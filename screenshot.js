import puppeteer from 'puppeteer';
import { program } from 'commander';

program
  .option('--url <char>', 'The URL')
  .option('--output <char>', 'The output filename')
  .option('--width <int>', 'The page width', 800)
  .option('--height <int>', 'The page height', 600);

program.parse();

const options = program.opts();

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox'],
  });
  const page = await browser.newPage();
  page.setDefaultNavigationTimeout(10000);
  await page.goto(options.url, { timeout: 5000 });
  await delay(1000);
  await page.setViewport({
    width: parseInt(options.width),
    height: parseInt(options.height),
  });
  await page.screenshot({
    path: options.output,
    clip: { x: 0, y: 0, width: parseInt(options.width), height: parseInt(options.height) },
  });
  await browser.close();
})();
