package com.jev.probe

import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.jev.probe.core.TrendCandle
import com.jev.probe.core.TrendData

class KlineActivity : AppCompatActivity() {
    private lateinit var chart: CandleView
    private lateinit var status: TextView
    private val picker = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri == null) return@registerForActivityResult
        try {
            val stream = contentResolver.openInputStream(uri) ?: error("文件无法读取")
            val rows = TrendData.fromCsv(stream)
            chart.setRows(rows)
            status.text = "已导入 ${rows.size} 个聊天日期；按每日消息方向净差计算。"
        } catch (e: Exception) {
            status.text = e.message ?: "CSV 导入失败"
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.decorView.setBackgroundColor(Color.rgb(246, 247, 244))
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(26, 52, 26, 28)
        }
        val title = TextView(this).apply {
            text = "关系走势 K 线"; textSize = 24f; setTextColor(Color.rgb(37, 66, 53))
        }
        root.addView(title)
        root.addView(TextView(this).apply {
            text = "选择示例走势，或导入带 timestamp,sender,message 列的聊天 CSV。"
            textSize = 13f; setPadding(0, 12, 0, 12)
        })
        val names = TrendData.examples.keys.toList()
        val select = Spinner(this)
        select.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, names)
        root.addView(select)
        val import = Button(this).apply { text = "导入聊天 CSV" }
        import.setOnClickListener { picker.launch(arrayOf("text/*", "application/csv")) }
        root.addView(import)
        chart = CandleView()
        root.addView(chart, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        status = TextView(this).apply { textSize = 13f; setPadding(0, 12, 0, 6) }
        root.addView(status)
        root.addView(TextView(this).apply {
            text = "图形展示消息方向净差，不代表爱意、回复率或关系成功率。转折要结合实际聊天事件判断。"
            textSize = 12f
        })
        select.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent: AdapterView<*>?) {}
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                chart.setRows(TrendData.example(names[position]))
                status.text = "${names[position]} · 示例走势"
            }
        }
        setContentView(root)
    }

    private inner class CandleView : View(this@KlineActivity) {
        private var rows: List<TrendCandle> = emptyList()
        private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
        fun setRows(value: List<TrendCandle>) { rows = value; invalidate() }

        override fun onDraw(canvas: Canvas) {
            super.onDraw(canvas)
            canvas.drawColor(Color.WHITE)
            if (rows.isEmpty()) return
            val low0 = rows.minOf { it.low }.toFloat()
            val high0 = rows.maxOf { it.high }.toFloat()
            val pad = maxOf(2f, (high0 - low0) * .15f)
            val low = low0 - pad; val high = high0 + pad
            val left = 36f; val right = width - 12f
            val top = 28f; val bottom = height - 52f
            fun y(value: Int) = bottom - (value - low) / (high - low) * (bottom - top)
            paint.color = Color.rgb(230, 235, 230); paint.strokeWidth = 1f
            repeat(5) { i ->
                val yy = top + i * (bottom - top) / 4
                canvas.drawLine(left, yy, right, yy, paint)
            }
            val span = (right - left) / rows.size
            rows.forEachIndexed { i, candle ->
                val x = left + (i + .5f) * span
                paint.color = if (candle.close >= candle.open) Color.rgb(41, 119, 93)
                              else Color.rgb(199, 117, 92)
                paint.strokeWidth = 3f
                canvas.drawLine(x, y(candle.high), x, y(candle.low), paint)
                val body = maxOf(2f, kotlin.math.abs(y(candle.open) - y(candle.close)))
                canvas.drawRect(x - minOf(20f, span * .3f), minOf(y(candle.open), y(candle.close)),
                    x + minOf(20f, span * .3f), minOf(y(candle.open), y(candle.close)) + body, paint)
                if (i % maxOf(1, rows.size / 5) == 0) {
                    paint.color = Color.DKGRAY; paint.textSize = 23f
                    canvas.drawText(candle.date.takeLast(5), x - 25, height - 16f, paint)
                }
            }
        }
    }
}
