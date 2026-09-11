# Final Git ve teslim kimliği

Test/ölçüm kanıtları `docs/verification/v2-evidence.json` ve onun referans verdiği tarihli dosyalarda Git ile izlenir. Paketleme testleri veya benchmarkları yeniden çalıştırmaz.

Bir commit kendi hash'ini veya kendi tree hash'ini içeren bir dosyayı saklayamaz: dosyaya hash yazılması tree'yi ve commit'i tekrar değiştirir. Bu nedenle `docs/verification/v2-summary.json` commit sonrası üretilen, `.gitignore` kapsamındaki teslim metadata'sıdır. Git'te saklanan kanıtın içeriğini korur ve gerçek `HEAD`, `HEAD^{tree}` ile `baseline_commit` değerlerini ekler. Commit kimlikleri için ikinci bir commit gerekmez.

Temiz `main` üzerinde commit/push sonrasında:

```powershell
python scripts/package_v2_delta.py --baseline 4a0f4c1cae879604a384e91862749fef754abecc --final-commit HEAD
```

Paketleyici çalışma ağacı temiz değilse, hedef HEAD değilse veya yasaklı dosya varsa durur. Binary delta yalnız baseline ile final commit arasındadır; izole Git index'e uygulandıktan sonra tree hash'i gerçek final tree ile eşit olmalıdır. Orijinal PDF/XLSX, özel `.env`, bağımlılıklar, cache ve runtime çıktıları commit/delta dışında kalır; orijinal kaynaklar tarihsel baseline'da bulunur; güncel dağıtımda kaynak çıkarımları ve hash manifesti korunur.

`handoff/GridSentinel-v2-delta/metadata.json` ve `verification/v2-summary.json` aynı final commit/tree kimliğini taşır. ZIP içinde üretilen summary `verification/` altındadır; kaynak delta'sının parçası değildir. Baseline'a patch uygulandıktan sonra bu summary yerel `docs/verification/v2-summary.json` yoluna kopyalanabilir; dosya Git dışında kalır. Kaynak patch'in tree'si ile final commit tree'si aynıdır.

Manifest dosya hash'leri, patch SHA256, summary SHA256, ZIP SHA256/CRC ve bilinen yerel secret taraması doğrulanır. ZIP, doğrulama raporu ve SHA256 sidecar `handoff/` içinde kalır; Git'e alınmaz. Mevcut handoff varsa üzerine yazılmaz; önce aynı dizinde farklı bir adla arşivlenir. Son `git status --short` boş ve `origin/main` HEAD ile aynı olmalıdır.

Kaynak PDF/XLSX silmeleri manifestte yalnız `deleted` olarak yer alır. Binary silmelerin tersine uygulama verisi patch'e alınmaz; böylece orijinaller delta içine yeniden gömülmez. İleri uygulama izole index üzerinde final tree ile doğrulanır. Geri dönüş için ters patch yerine Git geçmişi kullanılır.

`submission/` yalnız yerel ön eleme dosyaları içindir; Git ve delta paketi dışında tutulur. Yeni dosyalar da `.gitignore` kapsamındadır. GitHub üzerindeki teknik kanıt bağlantıları izlenen `v2-evidence.json` dosyasına gider.
