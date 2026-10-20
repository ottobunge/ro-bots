//! Incremental framing regressions using the Python SSE serializer.
#![allow(clippy::unwrap_used, clippy::indexing_slicing)]
use world_feed::live::SseDecoder;
#[test]
fn sse_accepts_every_chunk_boundary_and_crlf() {
    let raw = include_str!("../../../fixtures/events.sse").replace('\n', "\r\n");
    for split in 0..=raw.len() {
        let mut d = SseDecoder::default();
        let mut events = d.push(&raw.as_bytes()[..split]).unwrap();
        events.extend(d.push(&raw.as_bytes()[split..]).unwrap());
        assert_eq!(events.len(), 2);
        assert_eq!(events[1].0, 1);
        assert_eq!(events[1].1.kind, "combat");
    }
}
#[test]
fn sse_does_not_dispatch_partial_event_or_unbounded_frame() {
    let mut d = SseDecoder::default();
    assert!(d.push(b"id: 3\ndata: {\"ts\":1").unwrap().is_empty());
    assert!(d.push(&vec![b'a'; 131_073]).is_err());
}
