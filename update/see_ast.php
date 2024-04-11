<?php
require __DIR__ . '/vendor/autoload.php';

use PhpParser\Error;
use PhpParser\NodeDumper;
use PhpParser\ParserFactory;
use PhpParser\PrettyPrinter;

use PhpParser\Node;
use PhpParser\Node\Expr\MethodCall;
use PhpParser\Node\Expr\FuncCall;
use PhpParser\Node\Expr\New_;
use PhpParser\Node\Expr\AssignRef;
use PhpParser\Node\Expr\Assign;
use PhpParser\Node\Stmt\ClassMethod;
use PhpParser\NodeTraverser;
use PhpParser\NodeVisitorAbstract;

ini_set('xdebug.max_nesting_level', 10000);


$parser = (new ParserFactory)->create(ParserFactory::ONLY_PHP5);
$traverser = new NodeTraverser();
$prettyPrinter = new PrettyPrinter\Standard;
$baseEncoding = "ISO-8859-1";

$traverser->addVisitor(new class extends NodeVisitorAbstract {
    public function enterNode(Node $node)
    {
        if ($node instanceof MethodCall) {
            foreach ($node->args as $arg) {
                if ($arg->byRef) {
                    $arg->byRef = false;
                }
            }
        } elseif ($node instanceof FuncCall) {
            foreach ($node->args as $arg) {
                if ($arg->byRef) {
                    $arg->byRef = false;
                }
            }
        } elseif ($node instanceof New_) {
            foreach ($node->args as $arg) {
                if ($arg->byRef) {
                    $arg->byRef = false;
                }
            }
        } elseif ($node instanceof ClassMethod) {
            foreach ($node->params as $arg) {
                if ($arg->byRef) {
                    $arg->byRef = false;
                }
            }
        } elseif ($node instanceof AssignRef) {
            return new Assign($node->var, $node->expr, $node->getAttributes());
        }
    }
});

function glob_recursive($folder, $pattern)
{
    $files = glob("$folder/$pattern", GLOB_BRACE);
    foreach ($files as $file) {
        try {
            global $baseEncoding;

            $code = file_get_contents($file);

            if (mb_detect_encoding($code, $baseEncoding)) {
                // $code = iconv($baseEncoding, "UTF-8", $code);
            }

            $code = preg_replace(
                ["/<\? /", "/<\?\n/", "/<\?\r/", "/<\?\t/"],
                ["<?php ", "<?php\n", "<?php\r", "<?php\t"],
                $code
            );

            global $parser;
            global $traverser;
            global $prettyPrinter;

            $stmts = $parser->parse($code);
            $stmts = $traverser->traverse($stmts);
            $code = $prettyPrinter->prettyPrintFile($stmts);

            file_put_contents($file, $code);
            // echo "$file\n";
        } catch (Error) {
            // echo 'Parse Error: ', $e->getMessage();
            echo "=> $file\n";
            // file_put_contents($file, $code);
        }
    }
    $folders = glob("$folder/*", GLOB_ONLYDIR);
    foreach ($folders as $f) {
        glob_recursive($f, $pattern);
    }
    ;
}
;

glob_recursive("/home/isaac/projects/sigesp_enterprise", "*.php");

// $dumper = new NodeDumper;
// echo $dumper->dump($stmts) . "\n";
