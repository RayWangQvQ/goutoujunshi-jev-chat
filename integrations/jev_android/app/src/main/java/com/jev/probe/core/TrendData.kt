package com.jev.probe.core

import java.io.InputStream
import java.io.ByteArrayOutputStream
import java.time.LocalDateTime

/** Message-direction balance: other +1, me -1. It is not a relationship score. */
data class TrendCandle(val date: String, val open: Int, val high: Int, val low: Int, val close: Int)

object TrendData {
    val examples: Map<String, List<List<Int>>> = linkedMapOf(
        "双向升温" to listOf(listOf(50,56,48,54), listOf(54,64,53,61), listOf(61,72,60,70),
            listOf(70,76,68,74), listOf(74,82,72,79), listOf(79,86,77,83)),
        "热聊后降温" to listOf(listOf(50,59,48,57), listOf(57,65,55,63), listOf(63,66,58,60),
            listOf(60,63,51,54), listOf(54,56,43,46), listOf(46,52,44,49), listOf(49,50,45,47),
            listOf(47,49,34,38)),
        "冲突后修复" to listOf(listOf(55,61,53,59), listOf(59,61,28,36), listOf(36,49,34,45),
            listOf(45,63,43,60), listOf(60,68,58,65)),
        "忙但仍兑现" to listOf(listOf(50,55,48,53), listOf(53,62,51,59), listOf(59,60,55,58),
            listOf(58,60,55,58), listOf(58,65,56,63), listOf(63,76,61,73), listOf(73,80,71,77)),
        "明确边界后收线" to listOf(listOf(50,54,48,51), listOf(51,53,38,41), listOf(41,42,35,37))
    )

    fun example(name: String): List<TrendCandle> =
        (examples[name] ?: error("没有这个示例走势")).mapIndexed { i, row ->
            TrendCandle("示例 ${i + 1}", row[0], row[1], row[2], row[3])
        }

    fun fromCsv(input: InputStream): List<TrendCandle> {
        val bytes = input.use { source ->
            val out = ByteArrayOutputStream()
            val chunk = ByteArray(8192)
            while (out.size() <= 4_000_000) {
                val n = source.read(chunk)
                if (n < 0) break
                out.write(chunk, 0, n)
            }
            out.toByteArray()
        }
        require(bytes.size <= 4_000_000) { "CSV 超过 4 MB，请缩小范围" }
        val text = bytes.toString(Charsets.UTF_8).removePrefix("\uFEFF")
        val records = parseCsv(text)
        require(records.isNotEmpty()) { "CSV 没有内容" }
        val header = records.first().map { it.trim() }
        val t = header.indexOf("timestamp"); val s = header.indexOf("sender"); val m = header.indexOf("message")
        require(t >= 0 && s >= 0 && m >= 0) { "CSV 需要 timestamp,sender,message 三列" }
        require(records.size in 2..20_001) { "聊天记录须为 1 到 20000 条" }
        val candles = ArrayList<TrendCandle>()
        var balance = 0
        var previous: LocalDateTime? = null
        for (record in records.drop(1)) {
            require(record.size > maxOf(t, s, m)) { "CSV 行列不完整" }
            val at = try { LocalDateTime.parse(record[t].trim().replace(' ', 'T')) }
                     catch (_: Exception) { throw IllegalArgumentException("timestamp 需要 YYYY-MM-DD HH:MM:SS") }
            require(previous == null || !at.isBefore(previous)) { "聊天时间须按升序排列" }
            previous = at
            val sender = record[s].trim()
            require(sender == "me" || sender == "other") { "sender 只接受 me／other" }
            require(record[m].isNotBlank()) { "存在空消息，请核对 CSV" }
            val date = at.toLocalDate().toString()
            if (candles.isEmpty() || candles.last().date != date)
                candles.add(TrendCandle(date, balance, balance, balance, balance))
            balance += if (sender == "other") 1 else -1
            val old = candles.last()
            candles[candles.lastIndex] = old.copy(high = maxOf(old.high, balance),
                low = minOf(old.low, balance), close = balance)
        }
        return candles
    }

    /** RFC-style quoted commas, escaped quotes and quoted newlines. */
    private fun parseCsv(text: String): List<List<String>> {
        val records = ArrayList<List<String>>()
        var row = ArrayList<String>()
        val cell = StringBuilder()
        var quoted = false
        var i = 0
        while (i < text.length) {
            val c = text[i]
            when {
                c == '"' && quoted && i + 1 < text.length && text[i + 1] == '"' -> {
                    cell.append('"'); i++
                }
                c == '"' -> quoted = !quoted
                c == ',' && !quoted -> { row.add(cell.toString()); cell.setLength(0) }
                (c == '\n' || c == '\r') && !quoted -> {
                    if (c == '\r' && i + 1 < text.length && text[i + 1] == '\n') i++
                    row.add(cell.toString()); cell.setLength(0)
                    if (row.any { it.isNotBlank() }) records.add(row)
                    row = ArrayList()
                }
                else -> cell.append(c)
            }
            i++
        }
        require(!quoted) { "CSV 引号没有闭合" }
        if (cell.isNotEmpty() || row.isNotEmpty()) {
            row.add(cell.toString())
            if (row.any { it.isNotBlank() }) records.add(row)
        }
        return records
    }
}
