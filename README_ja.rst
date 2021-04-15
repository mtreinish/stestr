stestr（日本語訳）
===================

.. image:: https://github.com/mtreinish/stestr/actions/workflows/main.yml/badge.svg?branch=main
    :target: https://github.com/mtreinish/stestr/actions/workflows/main.yml
    :alt: CI Testing status

.. image:: https://img.shields.io/coveralls/github/mtreinish/stestr/main.svg?style=flat-square
    :target: https://coveralls.io/github/mtreinish/stestr?branch=main
    :alt: Code coverage

.. image:: https://img.shields.io/pypi/v/stestr.svg?style=flat-square
    :target: https://pypi.python.org/pypi/stestr
    :alt: Latest Version

.. image:: https://img.shields.io/github/license/mtreinish/stestr.svg?style=flat-square
    :target: https://opensource.org/licenses/Apache-2.0
    :alt: License

* 他の言語で読む場合はこちら: `English`_, `日本語`_
* フルレンダリングされたドキュメントはこちら: http://stestr.readthedocs.io/en/latest/
* プロジェクトのコードは GitHub にあります: https://github.com/mtreinish/stestr

.. _English: https://github.com/mtreinish/stestr/blob/main/README.rst
.. _日本語: https://github.com/mtreinish/stestr/blob/main/README_ja.rst

.. note:: stestr v2.x.x リリースシリーズは、Python 2 をサポートする最後のシリ
    ーズとなります。Python 2.7のサポートは「stestr リリース 3.0.0」
    にて打ち切られました。

概要
----
stestr は、パラレル Python テスト実行プログラムであり、一つのテストスイート
を、分割実行するために、複数プロセスを使い、 `unittest`_ テストスイートを、
実行するようデザインされています。また、実行失敗のデバッグや実行速度改善に向け
たスケジューラ最適化のために、すべてのテスト実行履歴を保存しています。この目標
達成のため、stestrでは、 `subunit`_ プロトコルを使用し、ストリーミングや、
複数ワーカーからの結果を保存することを容易にしています。

.. _unittest: https://docs.python.org/3/library/unittest.html
.. _subunit: https://github.com/testing-cabal/subunit

stestr は、元々 `testrepository`_ プロジェクトのフォークとして始まりました。
しかし、subunit を使用する testrepository のようなあらゆるテストランナー
インターフェースとなる代わりに、stestr は、python プロジェクトに特化・集中
したテストランナーです。stestr は、元々 testrepository からフォークしました
が、testrepository との後方互換性はありません。高いレベルでの基本的な実行
コンセプトは、それら2つのプロジェクトの間で共有されているものの、実際の使用法
は、完全に同一というわけでありません。

.. _testrepository: https://testrepository.readthedocs.org/en/latest


stestr のインストール
-----------------------

stestr は、pypi 経由で利用可能です。そのため、以下を実行するだけで::

  pip install -U stestr

あなたのシステムに、stestr を取得することができます。もし、開発バージョンの
stestr を使う必要があれば、リポジトリをクローンし、ローカルにインストール
することができます::

  git clone https://github.com/mtreinish/stestr.git && pip install -e stestr

この操作で、stestr をあなたの python 環境のローカル開発環境に対し、編集可能
モードでインストールできます。

stestr の利用
-----------------

stestr のインストール後、テスト実行のために使う方法は、とても簡単です。まずはじめに、
``.stestr.conf`` ファイルをあなたのプロジェクトのために作成します。この
ファイルは、「どこにテストがあるのか」「どうやってテストを実行する
のか」という基本的な情報を stestr に伝えます。基本最小限の内容例としては次の
ようなものとなります::

  [DEFAULT]
  test_path=./project_source_dir/tests

この記述は、テスト探索のために使われるディレクトリの相対パスを、stestr に伝え
ます。これは、標準的な `unittest discovery`_ の ``--start-directory`` と
同様です。

.. _unittest discovery: https://docs.python.org/3/library/unittest.html#test-discovery

あるいは、`tox <https://tox.readthedocs.io/en/latest/>`__
を使用している場合は、tox.ini ファイルを使用してstestrを構成できます。
たとえば::

  [stestr]
  test_path=./project_source_dir/tests

と設定すれば、stestr を使い始めるためにやるべきことはすべて完了です。テストを実行するためには、
単に次のように使うだけです::

    stestr run

これにより、まず、結果を保持するためのリポジトリが、カレントワーキング
ディレクトリの ``.stestr/`` に作成され、テスト探索により見つかったテストが
すべて実行されます。もし、あなたが、単にひとつのテスト（あるいはモジュール）を
実行し、テスト探索によるオーバーヘッドを避けたいのであれば、``--no-discover``
もしくは ``-n`` オプションをそのテストに対して指定し、実行することにより
可能です。

これらのコマンドの詳細は、さらなるオプションの説明は、stestr マニュアルを
参照してください: https://stestr.readthedocs.io/en/latest/MANUAL.html


testrepository からの移行
-----------------------------

もし、testrepository を既に使用しているプロジェクトを持っているのであれば、
stestr のソースリポジトリには、あなたのリポジトリを stestr を利用するように
移行するための、ヘルパースクリプトがあります。このスクリプトは、単に、
``.testr.conf`` ファイルから、 ``.stestr.conf`` ファイルを作成します。
（標準的な subunit.run テストコマンド形式を利用していることを想定しています）
これを実行するためには、あなたのプロジェクトリポジトリで、以下を実行します::

    $STESTR_SOURCE_DIR/tools/testr_to_stestr.py

これにより、 ``.stestr.conf`` が作成されます。


manpage の生成
------------------

stestr マニュアルは、htmlと同様に、manpage としてもレンダリングするために整形
されています。html 出力物と自動生成され公開されているものはこちらです:
https://stestr.readthedocs.io/en/latest/MANUAL.html しかしながら、その manpage
は、手動で生成する必要があります。このためには、手動で sphinx-build コマンドを
manpage builder とともに実行する必要があります。これは、簡単なスクリプトで
自動化されており、 stestr リポジトリのルートディレクトリで以下を実行します::

  tools/build_manpage.sh

これにより、troff ファイルが doc/build/man/stestr.1 に作成され、それは、
パッケージ可能で、あなたのシステムの man page としても配置可能です。

コントリビューション方法
------------------------

最新コードの参照: https://github.com/mtreinish/stestr
最新コードのクローン: ``git clone https://github.com/mtreinish/stestr.git``

コントリビューションのガイドラインドキュメント: http://stestr.readthedocs.io/en/latest/developer_guidelines.html

パッチを出すためには、`github pull requests`_ を使用してください。
プルリクエストを出す前には、手元の環境で ``tox`` を実行して、すべての自動
テストがパスすることを確認してください。これは、CI環境で実行されるものと同様の
テストスイートならびに、自動スタイルチェックを実行します。もし、あなたの変更に
より、CI が fail となった場合、その変更はマージすることができません。

.. _github pull requests: https://help.github.com/articles/about-pull-requests/

コミュニティ
-------------

GitHub でのやり取りに加え、stestr の IRC チャネルもあります:

Freenode の #stestr チャネル

stestr に関する質問、もしくは議論をしていますので、気軽に参加してください。
