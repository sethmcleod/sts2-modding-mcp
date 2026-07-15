using System;
using System.Collections.Generic;
using System.Linq;

namespace MCPTest;

/// <summary>
/// Captures unhandled exceptions into a ring buffer for surfacing via the bridge.
/// </summary>
public static class ExceptionMonitor
{
    private static readonly object Lock = new();
    private static readonly LinkedList<ExceptionRecord> Buffer = new();
    private const int MaxEntries = 100;
    private static int _nextId = 1;

    public sealed class ExceptionRecord
    {
        public int Id { get; init; }
        public DateTime Timestamp { get; init; }
        public string Type { get; init; } = "";
        public string Message { get; init; } = "";
        public string StackTrace { get; init; } = "";
        public string Source { get; init; } = "";
    }

    public static void Initialize()
    {
        AppDomain.CurrentDomain.UnhandledException += (_, args) =>
        {
            if (args.ExceptionObject is Exception ex)
                Record(ex, "UnhandledException");
        };

        System.Threading.Tasks.TaskScheduler.UnobservedTaskException += (_, args) =>
        {
            Record(args.Exception, "UnobservedTaskException");
            args.SetObserved();
        };
    }

    public static void Record(Exception ex, string source = "")
    {
        // AggregateException / TargetInvocationException wrap the real error in a generic
        // "a Task's exception was not observed" / "an exception was thrown by the target"
        // message with no useful stack. Unwrap to the innermost exception so tests see the
        // actual type, message, and stack (which is what tells a real mod bug apart from
        // harness noise).
        var real = Unwrap(ex);
        lock (Lock)
        {
            Buffer.AddLast(new ExceptionRecord
            {
                Id = _nextId++,
                Timestamp = DateTime.Now,
                Type = real.GetType().FullName ?? real.GetType().Name,
                Message = real.Message,
                StackTrace = real.StackTrace ?? "",
                Source = source,
            });
            while (Buffer.Count > MaxEntries)
                Buffer.RemoveFirst();
        }
        ModEntry.WriteLog($"[Exception] {source}: {real.GetType().Name}: {real.Message}");
    }

    private static Exception Unwrap(Exception ex)
    {
        while (true)
        {
            if (ex is AggregateException agg && agg.InnerExceptions.Count == 1)
                ex = agg.InnerExceptions[0];
            else if (ex.InnerException != null &&
                     (ex is System.Reflection.TargetInvocationException || ex.StackTrace == null))
                ex = ex.InnerException;
            else
                return ex;
        }
    }

    public static List<ExceptionRecord> GetRecent(int maxCount = 20, int sinceId = 0)
    {
        lock (Lock)
        {
            return Buffer
                .Where(r => r.Id > sinceId)
                .TakeLast(maxCount)
                .ToList();
        }
    }

    public static void Clear()
    {
        lock (Lock) { Buffer.Clear(); }
    }
}
