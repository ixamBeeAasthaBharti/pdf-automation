<?php
declare(strict_types=1);

/* ── Load .env from project root ── */
$envPath = __DIR__ . '/../.env';
if (file_exists($envPath)) {
    foreach (file($envPath, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
        $line = trim($line);
        if ($line === '' || str_starts_with($line, '#')) continue;
        if (str_contains($line, '=')) {
            [$key, $val] = explode('=', $line, 2);
            putenv(trim($key) . '=' . trim($val));
        }
    }
}

/* ── Validate ?id= param ── */
$mysqlId = isset($_GET['id']) ? (int) $_GET['id'] : 0;
if ($mysqlId <= 0) {
    http_response_code(400);
    die('<p style="font-family:sans-serif;color:red">Error: Please provide a valid document ID. Example: master.php?id=1474</p>');
}

/* ── MySQL connection ── */
$host   = getenv('MYSQL_HOST')     ?: '127.0.0.1';
$port   = (int)(getenv('MYSQL_PORT') ?: 3306);
$user   = getenv('MYSQL_USER')     ?: '';
$pass   = getenv('MYSQL_PASSWORD') ?: '';
$dbname = getenv('MYSQL_DB')       ?: '';

$dsn = "mysql:host={$host};port={$port};dbname={$dbname};charset=utf8mb4";
try {
    $pdo = new PDO($dsn, $user, $pass, [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_TIMEOUT            => 10,
    ]);
} catch (PDOException $e) {
    http_response_code(500);
    die('<p style="font-family:sans-serif;color:red">DB connection failed: ' . htmlspecialchars($e->getMessage()) . '</p>');
}

/* ── Fetch document ── */
$stmt = $pdo->prepare(
    'SELECT mysql_id, html_content, status FROM htmltopdfautomation WHERE mysql_id = :id LIMIT 1'
);
$stmt->execute([':id' => $mysqlId]);
$doc = $stmt->fetch();

if (!$doc) {
    http_response_code(404);
    die('<p style="font-family:sans-serif;color:red">Document ID <strong>' . $mysqlId . '</strong> not found.</p>');
}
if (empty($doc['html_content'])) {
    http_response_code(404);
    die('<p style="font-family:sans-serif;color:red">Document <strong>' . $mysqlId . '</strong> has no HTML content yet (status: ' . htmlspecialchars($doc['status']) . ').</p>');
}

/* ── Rewrite image paths ── */
$imgBase = '/storage/outputs/' . $mysqlId . '/images/';
$rawHtml = $doc['html_content'];
$rawHtml = str_replace('src="images/',    'src="' . $imgBase, $rawHtml);
$rawHtml = str_replace("src='images/",    "src='" . $imgBase, $rawHtml);
$rawHtml = str_replace('src="../images/', 'src="' . $imgBase, $rawHtml);

/* ── Extract page title ── */
$pageTitle = 'Study Notes';
if (preg_match('/<p[^>]*class="[^"]*cover-subtitle[^"]*"[^>]*>(.*?)<\/p>/si', $rawHtml, $m)) {
    $pageTitle = html_entity_decode(trim(strip_tags($m[1])), ENT_QUOTES, 'UTF-8');
} elseif (preg_match('/<title[^>]*>(.*?)<\/title>/si', $rawHtml, $m)) {
    $extracted = html_entity_decode(trim(strip_tags($m[1])), ENT_QUOTES, 'UTF-8');
    $pageTitle = preg_replace('/^Study Notes:\s*/i', '', $extracted);
}

/* ── Extract <body> content only ── */
$bodyContent = $rawHtml;
if (preg_match('/<body[^>]*>(.*?)<\/body>/si', $rawHtml, $bm)) {
    $bodyContent = $bm[1];
}

/* Remove the old embedded sticky header (master.php renders its own) */
$bodyContent = preg_replace('/<header\s[^>]*class="[^"]*doc-header[^"]*"[^>]*>.*?<\/header>/si', '', $bodyContent);

/* Format cover title for documents where topic is in cover-subtitle */
$bodyContent = preg_replace(
    '/(<h1[^>]*class="[^"]*cover-title[^"]*"[^>]*>)(.*?)(<\/h1>)\s*<p[^>]*class="[^"]*cover-subtitle[^"]*"[^>]*>(.*?)<\/p>/si',
    '<p class="cover-study-notes">$2</p>$1$4$3',
    $bodyContent
);

/* Format cover title for documents where title and topic are combined in a single cover-title */
$bodyContent = preg_replace(
    '/(<h1[^>]*class="[^"]*cover-title[^"]*"[^>]*>)\s*Study Notes:\s*(.*?)(<\/h1>)/si',
    '<p class="cover-study-notes">Study Notes</p>$1$2$3',
    $bodyContent
);

/* Remove inline scripts (replaced by reader.js) */
$bodyContent = preg_replace('/<script\b[^>]*>.*?<\/script>/si', '', $bodyContent);

$logoSrc = '../assets/logo.png';
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title><?php echo htmlspecialchars($pageTitle, ENT_QUOTES, 'UTF-8'); ?></title>
  <meta name="description" content="ixamBee Study Notes - <?php echo htmlspecialchars($pageTitle, ENT_QUOTES, 'UTF-8'); ?>"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
   <link href="https://fonts.googleapis.com/css2?family=Literata:ital,opsz,wght@0,7..72,200..900;1,7..72,200..900&display=swap" rel="stylesheet">
</head>
<body>

<header class="doc-header">
  <div class="doc-header-inner">
    <div class="title"><?php echo htmlspecialchars($pageTitle, ENT_QUOTES, 'UTF-8'); ?></div>
    <div class="header-right">
      <div class="header-font-control">
        <button id="font-size-dec" class="font-btn-sep" aria-label="Decrease font size" title="Decrease font size">A&minus;</button>
        <button id="font-size-inc" class="font-btn-sep" aria-label="Increase font size" title="Increase font size">A+</button>
      </div>
      <div class="header-logo-wrap">
        <img src="<?php echo htmlspecialchars($logoSrc, ENT_QUOTES, 'UTF-8'); ?>" alt="ixamBee Logo" class="header-logo-img"/>
      </div>
    </div>
  </div>
  <div id="read-progress" class="read-progress"></div>
</header>

<?php echo $bodyContent; ?>

<script src="reader.js"></script>
</body>
</html>