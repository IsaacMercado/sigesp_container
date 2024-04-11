<?php

declare(strict_types=1);

use Rector\CodeQuality\Rector\Class_\InlineConstructorDefaultToPropertyRector;
use Rector\Config\RectorConfig;
use Rector\Set\ValueObject\LevelSetList;

return static function (RectorConfig $rectorConfig): void {
    $rectorConfig->paths([
        // __DIR__ . '/mnt/c/laragon/www/sigesp/cfg/sigesp_cfg_d_ctrl_numero.php',
        '/home/isaac/projects/sigesp_enterprise/',
    ]);

    // $rectorConfig->disableParallel();
    $rectorConfig->parallel(240, 4, 2);
    $rectorConfig->noDiffs();

    // register a single rule
    // $rectorConfig->rule(InlineConstructorDefaultToPropertyRector::class);

    // define sets of rules
    $rectorConfig->sets([
        LevelSetList::UP_TO_PHP_82
    ]);
};